from fastapi import APIRouter, Depends, HTTPException, Body
from psycopg2.extensions import connection

from app.api.deps import get_db_conn, get_current_user
from app.repositories.resume_repo import resume_repo
from app.schemas.resume import ResumeCreate, ResumeResponse # 스키마 import 확인
from typing import List
router = APIRouter()
@router.get("/", response_model=List[ResumeResponse])
def get_my_resumes(
    current_user: dict = Depends(get_current_user),
    conn: connection = Depends(get_db_conn)
):
    """
    [내 이력서 목록 조회]
    로그인한 사용자의 모든 이력서를 최신순으로 반환합니다.
    (프론트엔드에서 면접 시작 전 이력서 선택 화면에 사용)
    """
    resumes = resume_repo.get_all_by_user_id(conn, current_user['user_id'])
    return resumes
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

@router.delete("/{resume_id}")
def delete_resume(
    resume_id: int,
    current_user: dict = Depends(get_current_user),
    conn: connection = Depends(get_db_conn)
):
    """
    [이력서 삭제]
    해당 ID의 이력서를 DB에서 삭제합니다. 
    본인의 이력서인지 확인하는 로직이 포함되어야 안전합니다.
    """
    # 1. 삭제 실행 (성공 여부를 반환받음)
    success = resume_repo.delete(conn, resume_id=resume_id, user_id=current_user['user_id'])
    
    # 2. 트랜잭션 확정
    conn.commit()

    if not success:
        raise HTTPException(status_code=404, detail="이력서를 찾을 수 없거나 삭제 권한이 없습니다.")

    return {"message": "Successfully deleted", "resume_id": resume_id}