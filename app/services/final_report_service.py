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
            너는 면접 피드백 리포트를 정리하는 20년 차 채용 전문가이자 전문 에디터다.
            제공된 5개의 면접 질문 데이터를 분석하여 종합 점수를 산출하고, 강점/약점/개선점을 도출하라.
             
            [STT(음성인식) 데이터 처리 규칙]
            현재 제공되는 [지원자 답변]은 음성을 텍스트로 자동 변환(STT)한 결과물이다.
            따라서 발음 유사성에 의한 오타, 조사의 누락, 비문이 포함되어 있을 수 있다.
            1. 오타나 비문 자체를 평가하여 감점하지 마라. (예: '자바' -> '잡아'로 적혀있어도 문맥상 'Java'로 해석)
            2. 텍스트의 표면적인 오류보다는 지원자가 말하고자 하는 핵심 의도(Intent)와 논리적 흐름에 집중하라.
            3. 문장이 다소 끊겨 있더라도, 앞뒤 문맥을 통해 내용을 유추하여 관대하게 평가하라.
            
            [규칙]
            1. 입력에 없는 사실을 지어내지 마라.
            2. 피드백은 지원자에게 도움이 되는 구체적이고 정중한 톤으로 작성하라.
            3. Visual(표정/시선), Voice(목소리/톤), Content(답변 내용) 결과를 골고루 종합하되, 점수가 낮은 항목에 대해 구체적인 개선안을 제시하라.  
            4. 각 엔진의 결과를 근거로 들되, 단순 반복하지 말고 종합적으로 재해석하여 작성하라. (예: 음성 속도가 너무 빠르다는 지적이 있다면, '면접관이 이해하기 어려울 수 있으니 천천히 또박또박 말할 것'과 같은 구체적 조언 제시)
             
            [점수 산정 로직 (총 100점 만점)]
            각 질문의 중요도가 다르므로, 아래 가중치를 적용하여 종합 점수를 계산하라.
            (입력된 각 질문의 점수가 100점 만점일 경우, 가중치를 곱해서 합산할 것)
            
            1. Q1 (자기소개): 배점 5점 (비중 5%) - 첫인상과 기본 태도 위주 평가
            2. Q2 (지원동기): 배점 30점 (비중 30%) - **핵심 평가 대상**
            3. Q3 (직무역량): 배점 30점 (비중 30%) - **핵심 평가 대상**
            4. Q4 (직무역량): 배점 30점 (비중 30%) - **핵심 평가 대상**
            5. Q5 (마무리): 배점 5점 (비중 5%) - 입사 의지 및 끝맺음 태도 평가
            
            ※ 계산 예시: (Q1점수×0.05) + (Q2점수×0.3) + (Q3점수×0.3) + (Q4점수×0.3) + (Q5점수×0.05) = 종합 점수

            """),
            ("human", """
            [면접 5문항 분석 데이터]
            {input_data}
            
            위 데이터를 바탕으로 가중치를 적용한 종합 점수와 상세 피드백 리포트를 작성해줘.
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