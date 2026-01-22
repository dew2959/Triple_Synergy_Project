import json
from typing import Any, Dict, List

# LangChain
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# Repositories & Utils
from app.core.config import settings
from app.repositories.final_report_repo import final_report_repo
from app.repositories.answer_repo import answer_repo
from app.repositories.visual_repo import visual_repo
from app.repositories.voice_repo import voice_repo
from app.repositories.content_repo import content_repo

# Schemas
from app.schemas.report import (
    FinalReportDBPayload,
    FinalReportResult,
    ModuleScoreSummary,
    StrengthWeakness,
    ActionPlan,
    FinalReportLLMOut  # 위에서 추가한 모델 임포트
)

# 점수 계산 헬퍼 함수 (기존 로직 유지)
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

# 데이터 축소 헬퍼 함수 (기존 로직 유지)
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
    def __init__(self):
        # 1. LangChain ChatOpenAI 초기화
        self.llm = ChatOpenAI(
            model="gpt-4o",  # 모델명
            api_key=settings.OPENAI_API_KEY,
            temperature=0.3
        )

    def create_or_upsert(self, conn, session_id: int):
        # 1. DB에서 답변 데이터 조회
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

        # 2. 점수 계산
        avg_v, avg_a, avg_c, total = _compute_session_scores(results)
        
        # 3. LLM 입력 데이터 준비
        compact_list = _build_session_compact(results)
        input_json_str = json.dumps(compact_list, ensure_ascii=False)

        # 4. LangChain 프롬프트 정의
        prompt = ChatPromptTemplate.from_messages([
            ("system", """
            너는 면접 피드백 리포트를 정리하는 전문 에디터다.
            제공된 면접 데이터를 분석하여 강점, 약점, 개선점을 도출하라.
            
            [규칙]
            1. 입력에 없는 사실을 지어내지 마라.
            2. 피드백은 지원자에게 도움이 되는 구체적이고 정중한 톤으로 작성하라.
            3. 각 항목(Visual, Voice, Content)별로 균형 있게 분석하라.
            """),
            ("human", """
            [면접 분석 데이터]
            {input_data}
            
            위 데이터를 바탕으로 종합 리포트를 작성해줘.
            """)
        ])

        # 5. 체인 생성 (Prompt -> LLM -> Structured Output)
        chain = prompt | self.llm.with_structured_output(FinalReportLLMOut)

        # 기본값 설정
        llm_data = FinalReportLLMOut(
            summary_headline="분석 완료",
            overall_feedback="AI 분석이 완료되었습니다. 상세 결과를 확인해주세요.",
            visual_strengths_json=[], visual_weaknesses_json=[],
            voice_strengths_json=[], voice_weaknesses_json=[],
            content_strengths_json=[], content_weaknesses_json=[],
            action_plans_json=[]
        )

        try:
            # 6. 체인 실행
            llm_data = chain.invoke({"input_data": input_json_str})
            
        except Exception as e:
            print(f"❌ [LangChain Error] Final Report Generation Failed: {e}")
            # 실패 시 위에서 만든 기본값(llm_data)이 사용됨

        # 7. DB 저장용 Payload 생성
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
            
            # ActionPlanItem 리스트를 dict 리스트로 변환
            action_plans_json=[ap.model_dump() for ap in llm_data.action_plans_json],
        )

        # 8. DB Upsert
        row = final_report_repo.upsert_final_report(conn, db_payload.model_dump())

        # 9. 결과 반환
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

# 싱글톤 인스턴스
final_report_service = FinalReportService()