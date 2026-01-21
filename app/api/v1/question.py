from fastapi import APIRouter, Depends, HTTPException
from psycopg2.extensions import connection
from typing import List

from app.api.deps import get_db_conn, get_current_user
from app.repositories.question_repo import question_repo
from app.schemas.question import QuestionCreate, QuestionResponse
from pydantic import BaseModel

router = APIRouter()

@router.post("/", response_model=QuestionResponse)
def create_question(
    question_in: QuestionCreate,
    conn: connection = Depends(get_db_conn),
    current_user: dict = Depends(get_current_user)
):
    """
    [질문 생성]
    특정 세션(session_id)에 속하는 면접 질문을 수동으로 추가합니다.
    """
    # 1. 스키마 -> 딕셔너리 변환
    q_data = question_in.model_dump() # Pydantic v2

    try:
        # 2. DB 저장
        new_question = question_repo.create(conn, q_data)
        conn.commit()
        return new_question
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"질문 저장 실패: {str(e)}")


@router.get("/session/{session_id}", response_model=List[QuestionResponse])
def get_questions_by_session(
    session_id: int,
    conn: connection = Depends(get_db_conn),
    current_user: dict = Depends(get_current_user)
):
    """
    [세션별 질문 목록 조회]
    특정 세션에 등록된 질문들을 순서대로 가져옵니다.
    """
    questions = question_repo.get_by_session_id(conn, session_id)
    return questions


