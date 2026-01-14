from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
import psycopg2
from app.core.config import settings

from app.api.deps import get_db_conn, get_current_user
from app.repositories.answer_repo import answer_repo
from app.repositories.session_repo import session_repo
from app.services.analysis_service import analysis_service

router = APIRouter()

# 백그라운드에서 실행될 래퍼 함수 (DB 연결을 새로 맺음)
def _background_analysis_task(answer_id: int, file_path: str):
    conn = None
    try:
        # DB 직접 연결 (백그라운드 스레드용)
        conn = psycopg2.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            dbname=settings.DB_NAME
        )
        # 서비스 호출
        analysis_service.run_full_analysis(conn, answer_id, file_path)
        conn.commit()
    except Exception as e:
        print(f"Background Task Error: {e}")
        if conn: conn.rollback()
    finally:
        if conn: conn.close()


@router.post("/session/{session_id}")
def analyze_session_answers(
    session_id: int,
    background_tasks: BackgroundTasks,
    conn=Depends(get_db_conn),
    current_user=Depends(get_current_user)
):
    # 1. 답변 목록 가져오기
    answers = answer_repo.get_all_by_session_id(conn, session_id)
    if not answers:
        raise HTTPException(status_code=400, detail="No answers to analyze.")

    # 2. 상태 업데이트
    session_repo.update_status(conn, session_id, "ANALYZING")
    conn.commit()

    # 3. 작업 등록
    count = 0
    for ans in answers:
        if ans['video_path']:
            background_tasks.add_task(
                _background_analysis_task, # 래퍼 함수 사용
                ans['answer_id'], 
                ans['video_path']
            )
            count += 1
            
    return {"message": "Analysis started", "queued_count": count}