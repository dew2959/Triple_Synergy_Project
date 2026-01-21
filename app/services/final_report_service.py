import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.repositories.final_report_repo import final_report_repo
from app.repositories.answer_repo import answer_repo
from app.repositories.visual_repo import visual_repo
from app.repositories.voice_repo import voice_repo
from app.repositories.content_repo import content_repo

# 🔴 [수정] Utils Import
from app.utils.report_llm_client import ReportLLMClient
from app.utils.prompt_utils import build_final_report_prompt, sanitize_text, filter_or_raise

# --- Pydantic Output Models for Final Report ---
class ActionPlanItem(BaseModel):
    title: str
    description: str

class FinalReportLLMOut(BaseModel):
    summary_headline: str
    overall_feedback: str
    visual_summary: Optional[str] = None
    voice_summary: Optional[str] = None
    content_summary: Optional[str] = None
    visual_strengths_json: List[str] = Field(default_factory=list)
    visual_weaknesses_json: List[str] = Field(default_factory=list)
    voice_strengths_json: List[str] = Field(default_factory=list)
    voice_weaknesses_json: List[str] = Field(default_factory=list)
    content_strengths_json: List[str] = Field(default_factory=list)
    content_weaknesses_json: List[str] = Field(default_factory=list)
    action_plans_json: List[ActionPlanItem] = Field(default_factory=list)

# --- Service Code ---

def _compute_session_scores(results: List[Dict[str, Any]]):
    v_scores, a_scores, c_scores = [], [], []
    for item in results:
        if item['visual'] and item['visual'].get('score') is not None:
            v_scores.append(item['visual']['score'])
        if item['voice'] and item['voice'].get('score') is not None:
            a_scores.append(item['voice']['score'])
        if item['content']:
            c_res = item['content']
            if c_res.get('score') is not None:
                c_scores.append(c_res['score'])
            else:
                l = c_res.get('logic_score', 0) or 0
                j = c_res.get('job_fit_score', 0) or 0
                t = c_res.get('time_management_score', 0) or 0
                c_scores.append(int((l+j+t)/3))

    avg_v = int(sum(v_scores)/len(v_scores)) if v_scores else 0
    avg_a = int(sum(a_scores)/len(a_scores)) if a_scores else 0
    avg_c = int(sum(c_scores)/len(c_scores)) if c_scores else 0
    
    valid = [s for s in [avg_v, avg_a, avg_c] if s > 0]
    total = int(sum(valid)/len(valid)) if valid else 0
    return avg_v, avg_a, avg_c, total

def _build_session_compact(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    compact_list = []
    for item in results:
        compact = {
            "question": item['question'],
            "visual": {"score": item['visual'].get('score', 0) if item['visual'] else 0},
            "voice": {"score": item['voice'].get('score', 0) if item['voice'] else 0},
            "content": {"feedback": item['content'].get('feedback', "") if item['content'] else ""}
        }
        compact_list.append(compact)
    return compact_list

class FinalReportService:
    def __init__(self, llm_client: ReportLLMClient):
        self.llm = llm_client

    def create_or_upsert(self, conn, session_id: int):
        from app.schemas.report import FinalReportDBPayload, FinalReportResult, ModuleScoreSummary, StrengthWeakness, ActionPlan

        answers = answer_repo.get_all_by_session_id(conn, session_id)
        if not answers:
            return None

        results = []
        for ans in answers:
            ans_id = ans["answer_id"]
            results.append({
                "question": ans.get("question_content", ""),
                "visual": visual_repo.get_by_answer_id(conn, ans_id),
                "voice": voice_repo.get_by_answer_id(conn, ans_id),
                "content": content_repo.get_by_answer_id(conn, ans_id),
            })

        avg_v, avg_a, avg_c, total = _compute_session_scores(results)
        compact_list = _build_session_compact(results)

        # 기본값 (실패 시)
        llm_data = FinalReportLLMOut(
            summary_headline="분석 완료",
            overall_feedback="AI 분석이 완료되었습니다."
        )

        try:
            prompt = build_final_report_prompt({"results": compact_list})
            # 🔴 [수정] 제네릭 generate 사용
            json_str = self.llm.generate(prompt, response_format=FinalReportLLMOut, temperature=0.3)
            llm_data = FinalReportLLMOut.model_validate_json(json_str)
        except Exception as e:
            print(f"❌ Final Report LLM Error: {e}")

        # DB Payload 생성
        db_payload = FinalReportDBPayload(
            session_id=session_id,
            total_score=total,
            summary_headline=llm_data.summary_headline,
            overall_feedback=llm_data.overall_feedback,
            avg_visual_score=avg_v,
            avg_voice_score=avg_a,
            avg_content_score=avg_c,
            visual_strengths_json=llm_data.visual_strengths_json,
            visual_weaknesses_json=llm_data.visual_weaknesses_json,
            voice_strengths_json=llm_data.voice_strengths_json,
            voice_weaknesses_json=llm_data.voice_weaknesses_json,
            content_strengths_json=llm_data.content_strengths_json,
            content_weaknesses_json=llm_data.content_weaknesses_json,
            action_plans_json=[ap.model_dump() for ap in llm_data.action_plans_json],
        )

        row = final_report_repo.upsert_final_report(conn, db_payload.model_dump())

        return FinalReportResult(
            session_id=row["session_id"],
            total_score=row["total_score"],
            summary_headline=row.get("summary_headline"),
            overall_feedback=row.get("overall_feedback"),
            visual=ModuleScoreSummary(avg_score=row["avg_visual_score"], summary=llm_data.visual_summary),
            voice=ModuleScoreSummary(avg_score=row["avg_voice_score"], summary=llm_data.voice_summary),
            content=ModuleScoreSummary(avg_score=row["avg_content_score"], summary=llm_data.content_summary),
            visual_points=StrengthWeakness(strengths=row.get("visual_strengths_json"), weaknesses=row.get("visual_weaknesses_json")),
            voice_points=StrengthWeakness(strengths=row.get("voice_strengths_json"), weaknesses=row.get("voice_weaknesses_json")),
            content_points=StrengthWeakness(strengths=row.get("content_strengths_json"), weaknesses=row.get("content_weaknesses_json")),
            action_plans=[ActionPlan(**ap) for ap in (row.get("action_plans_json") or [])],
            created_at=str(row.get("created_at"))
        )