from fastapi import APIRouter, Depends, HTTPException
from psycopg2.extensions import connection

from app.api.deps import get_db_conn, get_current_user
from app.repositories.visual_repo import visual_repo
from app.repositories.voice_repo import voice_repo
from app.repositories.content_repo import content_repo
from app.repositories.final_report_repo import final_report_repo
from app.repositories.answer_repo import answer_repo


# 스키마 import
from app.schemas.result import (
    VisualResultResponse, VoiceResultResponse, ContentResultResponse,
    SessionFullResultResponse, AnswerFullResult
)
from app.schemas.report import FinalReportResult, ModuleScoreSummary, StrengthWeakness, ActionPlan

router = APIRouter()

# ==========================================
# 1. 개별 분석 결과 조회 (Visual, Voice, Content)
# ==========================================

@router.get("/answer/{answer_id}/visual", response_model=VisualResultResponse)
def get_visual_result(
    answer_id: int,
    conn: connection = Depends(get_db_conn),
    current_user: dict = Depends(get_current_user)
):
    result = visual_repo.get_by_answer_id(conn, answer_id)
    if not result:
        raise HTTPException(status_code=404, detail="Visual analysis not found")
    return result

@router.get("/answer/{answer_id}/voice", response_model=VoiceResultResponse)
def get_voice_result(
    answer_id: int,
    conn: connection = Depends(get_db_conn),
    current_user: dict = Depends(get_current_user)
):
    result = voice_repo.get_by_answer_id(conn, answer_id)
    if not result:
        raise HTTPException(status_code=404, detail="Voice analysis not found")
    return result

@router.get("/answer/{answer_id}/content", response_model=ContentResultResponse)
def get_content_result(
    answer_id: int,
    conn: connection = Depends(get_db_conn),
    current_user: dict = Depends(get_current_user)
):
    result = content_repo.get_by_answer_id(conn, answer_id)
    if not result:
        raise HTTPException(status_code=404, detail="Content analysis not found")
    return result


# ==========================================
# 2. 최종 리포트 조회 (Final Report)
# ==========================================

@router.get("/session/{session_id}/report", response_model=FinalReportResult)
def get_final_report(
    session_id: int,
    conn: connection = Depends(get_db_conn),
    current_user: dict = Depends(get_current_user)
):
    """
    세션 ID에 해당하는 최종 리포트를 조회합니다.
    (FinalReportService에서 만든 구조 그대로 반환)
    """
    row = final_report_repo.get_by_session_id(conn, session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Final report not found. (Not generated yet?)")

    
    from app.schemas.report import ModuleScoreSummary, StrengthWeakness, ActionPlan

    return FinalReportResult(
        session_id=row["session_id"],
        total_score=row["total_score"],
        summary_headline=row.get("summary_headline") or "",
        overall_feedback=row.get("overall_feedback") or "",

        # 요약 텍스트는 DB 컬럼이 따로 없어서 빈칸 처리하거나, 
        # 필요하다면 DB에 summary 컬럼들을 추가해야 함. (현재는 점수만)
        visual=ModuleScoreSummary(avg_score=row["avg_visual_score"], summary=None),
        voice=ModuleScoreSummary(avg_score=row["avg_voice_score"], summary=None),
        content=ModuleScoreSummary(avg_score=row["avg_content_score"], summary=None),

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
        created_at=str(row.get("created_at"))
    )


@router.get("/session/{session_id}/full", response_model=SessionFullResultResponse)
def get_session_full_result(
    session_id: int,
    conn: connection = Depends(get_db_conn),
    current_user: dict = Depends(get_current_user)
):
    """
    [세션 종합 결과]
    최종 리포트(Final Report)와 
    모든 질문에 대한 개별 분석 결과(Visual, Voice, Content)를 한 번에 반환합니다.
    """
    
    # 1. 최종 리포트 조회
    report_row = final_report_repo.get_by_session_id(conn, session_id)
    final_report_data = None
    
    if report_row:
        # DB Row -> Pydantic 변환
        final_report_data = FinalReportResult(
            session_id=report_row["session_id"],
            total_score=report_row["total_score"],
            summary_headline=report_row.get("summary_headline") or "",
            overall_feedback=report_row.get("overall_feedback") or "",
            
            visual=ModuleScoreSummary(avg_score=report_row["avg_visual_score"], summary=None),
            voice=ModuleScoreSummary(avg_score=report_row["avg_voice_score"], summary=None),
            content=ModuleScoreSummary(avg_score=report_row["avg_content_score"], summary=None),

            visual_points=StrengthWeakness(
                strengths=report_row.get("visual_strengths_json") or [],
                weaknesses=report_row.get("visual_weaknesses_json") or [],
            ),
            voice_points=StrengthWeakness(
                strengths=report_row.get("voice_strengths_json") or [],
                weaknesses=report_row.get("voice_weaknesses_json") or [],
            ),
            content_points=StrengthWeakness(
                strengths=report_row.get("content_strengths_json") or [],
                weaknesses=report_row.get("content_weaknesses_json") or [],
            ),

            action_plans=[ActionPlan(**ap) for ap in (report_row.get("action_plans_json") or [])],
            created_at=str(report_row.get("created_at"))
        )

    # 2. 답변 목록 및 개별 분석 결과 조회
    answers_data = []
    answers_rows = answer_repo.get_all_by_session_id(conn, session_id)
    
    for row in answers_rows:
        ans_id = row['answer_id']
        
        # 각 분석 결과 조회 (없으면 None)
        v_res = visual_repo.get_by_answer_id(conn, ans_id)
        a_res = voice_repo.get_by_answer_id(conn, ans_id)
        c_res = content_repo.get_by_answer_id(conn, ans_id)
        
        answers_data.append(AnswerFullResult(
            question_id=row['question_id'],
            question_content=row['question_content'],
            answer_id=ans_id,
            stt_text=row['stt_text'],
            video_path=row['video_path'],
            created_at=row['created_at'],
            
            # Pydantic 모델로 변환 (데이터가 있을 때만)
            visual=VisualResultResponse(**v_res) if v_res else None,
            voice=VoiceResultResponse(**a_res) if a_res else None,
            content=ContentResultResponse(**c_res) if c_res else None
        ))

    # 3. 통합 결과 반환
    return SessionFullResultResponse(
        session_id=session_id,
        final_report=final_report_data,
        answers=answers_data
    )