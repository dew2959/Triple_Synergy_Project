import json
from typing import Any, Dict, Optional, List

from app.schemas.report import (
    FinalReportDBPayload,
    FinalReportResult,
    ModuleScoreSummary,
    StrengthWeakness,
    ActionPlan,
)
from app.repositories.final_report_repo import final_report_repo
from app.repositories.answer_repo import answer_repo
from app.repositories.visual_repo import visual_repo
from app.repositories.voice_repo import voice_repo
from app.repositories.content_repo import content_repo
from app.utils.prompt_utils import build_final_report_prompt, sanitize_text, filter_or_raise


def _safe_int(x) -> Optional[int]:
    try:
        if x is None:
            return None
        return int(round(float(x)))
    except Exception:
        return None

def _compute_session_scores(results: List[Dict[str, Any]]):
    """
    세션 전체의 평균 점수 계산
    results = [{"visual": {...}, "voice": {...}, "content": {...}}, ...]
    """
    v_scores = []
    a_scores = []
    c_scores = []

    for item in results:
        # 1. Visual
        if item['visual'] and item['visual'].get('score') is not None:
            v_scores.append(item['visual']['score'])

        # 2. Voice
        if item['voice'] and item['voice'].get('score') is not None:
            a_scores.append(item['voice']['score'])

        # 3. Content (수정됨: score가 없으면 하위 점수 평균 계산)
        if item['content']:
            c_res = item['content']
            
            # (A) 만약 DB에 score 컬럼이 있고 값이 있다면 우선 사용
            if c_res.get('score') is not None:
                c_scores.append(c_res['score'])
            
            # (B) 없다면 하위 3개 항목의 평균으로 계산
            else:
                l_score = c_res.get('logic_score', 0) or 0
                j_score = c_res.get('job_fit_score', 0) or 0
                t_score = c_res.get('time_management_score', 0) or 0
                
                calculated_score = int((l_score + j_score + t_score) / 3)
                c_scores.append(calculated_score)

    # 모듈별 평균 계산
    avg_v = int(sum(v_scores) / len(v_scores)) if v_scores else 0
    avg_a = int(sum(a_scores) / len(a_scores)) if a_scores else 0
    avg_c = int(sum(c_scores) / len(c_scores)) if c_scores else 0
    
    # 전체 종합 평균 (0점이 아닌 유효한 점수들만 평균 내기)
    valid_avgs = [s for s in [avg_v, avg_a, avg_c] if s > 0]
    total = int(sum(valid_avgs) / len(valid_avgs)) if valid_avgs else 0

    return avg_v, avg_a, avg_c, total


def _build_session_compact(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    LLM에게 보낼 데이터 구조 생성 (여러 질문-답변 리스트)
    """
    compact_list = []
    
    for item in results:
        # 각 답변의 핵심 정보만 추림
        compact = {
            "question": item['question'],  # 질문 텍스트
            "visual": {
                "score": item['visual'].get('score') if item['visual'] else 0,
                "feedback": item['visual'].get('feedback') if item['visual'] else ""
            },
            "voice": {
                "score": item['voice'].get('score') if item['voice'] else 0,
                "feedback": item['voice'].get('feedback') if item['voice'] else ""
            },
            "content": {
                "score": item['content'].get('score') if item['content'] else 0,
                "feedback": item['content'].get('feedback') if item['content'] else ""
            }
        }
        compact_list.append(compact)
        
    return compact_list



def _fallback_llm_payload() -> Dict[str, Any]:
    return {
        "summary_headline": "면접 분석 완료",
        "overall_feedback": "모든 답변에 대한 분석이 완료되었습니다. 각 질문별 상세 결과를 확인해보세요.",
        "visual_summary": "분석 데이터 부족",
        "voice_summary": "분석 데이터 부족",
        "content_summary": "분석 데이터 부족",
        "visual_strengths_json": [], "visual_weaknesses_json": [],
        "voice_strengths_json": [], "voice_weaknesses_json": [],
        "content_strengths_json": [], "content_weaknesses_json": [],
        "action_plans_json": [],
    }


class FinalReportService:
    def __init__(self, llm_client):
        self.llm = llm_client

    def create_or_upsert(self, conn, session_id: int) -> FinalReportResult:
        # 1. 세션의 모든 답변 조회
        answers = answer_repo.get_all_by_session_id(conn, session_id)

        if not answers:
            print(f"⚠️ 세션 {session_id}에 대한 답변이 없습니다.")
            return None  # (원래 타입과 맞추려면 error 처리 방식으로 바꾸는 것도 고려)

        # 2. 각 답변별 분석 결과 수집
        results = []
        for ans in answers:
            ans_id = ans["answer_id"]
            v_res = visual_repo.get_by_answer_id(conn, ans_id)
            a_res = voice_repo.get_by_answer_id(conn, ans_id)
            c_res = content_repo.get_by_answer_id(conn, ans_id)

            results.append({
                "question": ans.get("question_content", "질문 내용 없음"),
                "visual": v_res,
                "voice": a_res,
                "content": c_res,
            })

        # 3. 점수 계산 (평균)
        avg_v, avg_a, avg_c, total = _compute_session_scores(results)

        # 4. LLM 프롬프트 생성 및 호출
        compact_list = _build_session_compact(results)

        try:
            # ✅ prompt_utils 기반 프롬프트 생성
            prompt = build_final_report_prompt(compact_list)

            # ✅ sanitize + filter (전송 직전 공통 방어)
            prompt = sanitize_text(prompt)
            filter_or_raise(prompt, where="final_report.prompt")

            raw = self.llm.generate(prompt, temperature=0.3)
            llm_json = json.loads(raw)

        except Exception as e:
            print(f"❌ Final Report LLM Error: {e}")
            llm_json = _fallback_llm_payload()

        # 5. DB 저장용 페이로드 생성
        db_payload = FinalReportDBPayload(
            session_id=session_id,
            total_score=total,
            summary_headline=llm_json.get("summary_headline") or "면접 피드백",
            overall_feedback=llm_json.get("overall_feedback") or "",

            avg_visual_score=avg_v,
            avg_voice_score=avg_a,
            avg_content_score=avg_c,

            visual_strengths_json=llm_json.get("visual_strengths_json") or [],
            visual_weaknesses_json=llm_json.get("visual_weaknesses_json") or [],
            voice_strengths_json=llm_json.get("voice_strengths_json") or [],
            voice_weaknesses_json=llm_json.get("voice_weaknesses_json") or [],
            content_strengths_json=llm_json.get("content_strengths_json") or [],
            content_weaknesses_json=llm_json.get("content_weaknesses_json") or [],

            action_plans_json=llm_json.get("action_plans_json") or [],
        )

        # 6. DB Upsert
        row = final_report_repo.upsert_final_report(conn, db_payload.model_dump())

        # 7. 결과 반환
        return FinalReportResult(
            session_id=row["session_id"],
            total_score=row["total_score"],
            summary_headline=row.get("summary_headline"),
            overall_feedback=row.get("overall_feedback"),

            visual=ModuleScoreSummary(avg_score=row["avg_visual_score"], summary=llm_json.get("visual_summary")),
            voice=ModuleScoreSummary(avg_score=row["avg_voice_score"], summary=llm_json.get("voice_summary")),
            content=ModuleScoreSummary(avg_score=row["avg_content_score"], summary=llm_json.get("content_summary")),

            visual_points=StrengthWeakness(
                strengths=row.get("visual_strengths_json") or [],
                weaknesses=row.get("visual_weaknesses_json") or [],
            ),
            voice_points=StrengthWeakness(
                strengths=row.get("voice_strengths_json") or [],
                weaknesses=row.get("voice_weaknesses_json") or [],
            ),
            content_points=StrengthWeakness(
                strengths=row.get("content_strengths_json") or [],
                weaknesses=row.get("content_weaknesses_json") or [],
            ),

            action_plans=[ActionPlan(**ap) for ap in (row.get("action_plans_json") or [])],
            created_at=str(row.get("created_at")) if row.get("created_at") else None,
        )
