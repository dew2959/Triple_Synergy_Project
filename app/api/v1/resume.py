from fastapi import APIRouter, Depends, HTTPException, Body
from psycopg2.extensions import connection

from app.api.deps import get_db_conn, get_current_user
from app.repositories.resume_repo import resume_repo
from app.schemas.resume import ResumeCreate, ResumeResponse # 스키마 import 확인

router = APIRouter()

# [변경] POST /upload -> / (또는 /create)
# 파일 업로드가 아니므로 경로를 명확히 하는 것이 좋습니다.
@router.post("/", response_model=ResumeResponse)
def create_resume_manual(
    resume_in: ResumeCreate,  # 👈 핵심: 프론트에서 보낸 JSON이 여기로 들어옵니다.
    current_user: dict = Depends(get_current_user),
    conn: connection = Depends(get_db_conn)
):
    """
    [이력서 직접 입력]
    프론트엔드 폼에서 입력받은 이력서 데이터를 DB에 저장합니다.
    """
    
    # 1. Pydantic 모델을 딕셔너리로 변환
    resume_data = resume_in.model_dump()

    # 2. DB 저장 (Repo 호출)
    new_resume = resume_repo.create(
        conn,
        user_id=current_user['user_id'],
        resume_data=resume_data
    )
    
    # 3. 트랜잭션 확정
    conn.commit()

    if not new_resume:
        raise HTTPException(status_code=500, detail="이력서 저장에 실패했습니다.")

    return new_resume