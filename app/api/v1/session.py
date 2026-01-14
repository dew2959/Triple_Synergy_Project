from fastapi import APIRouter, Depends, HTTPException
from psycopg2.extensions import connection
from typing import List

from app.api.deps import get_db_conn, get_current_user
from app.repositories.session_repo import session_repo
from app.repositories.resume_repo import resume_repo
from app.schemas.session import SessionCreate, SessionResponse

router = APIRouter()

@router.get("/", response_model=List[SessionResponse])
def get_my_sessions(
    conn: connection = Depends(get_db_conn),
    current_user: dict = Depends(get_current_user)
):
    """
    [내 면접 세션 목록 조회]
    로그인한 사용자의 모든 면접 세션 기록을 최신순으로 반환합니다.
    """
    return session_repo.get_all_by_user_id(conn, current_user['user_id'])

@router.post("/", response_model=SessionResponse)
def create_interview_session(
    session_in: SessionCreate,
    conn: connection = Depends(get_db_conn),
    current_user: dict = Depends(get_current_user)
):
    """
    [면접 세션 생성]
    1. resume_id를 보낸 경우 -> 그 이력서 사용
    2. resume_id를 안 보낸 경우 -> 내 가장 최신 이력서 사용
    """
    user_id = current_user['user_id']
    resume_target = None

    # (A) ID를 직접 지정한 경우
    if session_in.resume_id:
        resume_target = resume_repo.get_by_id(conn, session_in.resume_id)
        if not resume_target:
            raise HTTPException(status_code=404, detail="지정한 이력서를 찾을 수 없습니다.")
        if resume_target['user_id'] != user_id:
            raise HTTPException(status_code=403, detail="본인의 이력서만 사용할 수 있습니다.")
            
    # (B) ID 없이 요청한 경우 -> 최신 이력서 자동 조회
    else:
        resume_target = resume_repo.get_latest_by_user_id(conn, user_id)
        if not resume_target:
            raise HTTPException(status_code=400, detail="등록된 이력서가 없습니다. 먼저 이력서를 등록해주세요.")

    # 3. 정보 추출 및 세션 생성 (공통 로직)
    job_role = resume_target.get('job_title') or "General"
    company_name = resume_target.get('target_company') or ""
    final_resume_id = resume_target['resume_id']

    try:
        new_session = session_repo.create(
            conn,
            user_id=user_id,
            resume_id=final_resume_id,
            job_role=job_role,
            company_name=company_name
        )
        conn.commit()
        return new_session
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"세션 생성 실패: {str(e)}")