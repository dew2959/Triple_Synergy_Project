import shutil
import os
from fastapi import APIRouter, UploadFile, File, Depends, Form, BackgroundTasks, HTTPException
from psycopg2.extensions import connection 

from app.api.deps import get_db_conn
from app.schemas.interview import AnswerResponse
from app.repositories.answer_repo import answer_repo
from app.services.analysis_service import analysis_service

# [핵심] 백그라운드 작업을 위해 가져옵니다.
from app.core.db import get_db_connection 

router = APIRouter()

# 영상 저장 경로 설정
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# =========================================================
#  Background Task Wrapper
# =========================================================
def run_background_analysis(answer_id: int, file_path: str):
    """
    백그라운드 작업: 요청(Request)과 독립적으로 실행됨.
    따라서 Depends로 받은 conn을 쓰면 안 되고(이미 닫힘),
    여기서 스스로 연결을 맺고 끊어야 합니다.
    """
    with get_db_connection() as conn:
        analysis_service.run_full_analysis(conn, answer_id, file_path)


# =========================================================
#  API Endpoints
# =========================================================

@router.post("/upload", response_model=AnswerResponse)
def upload_interview_video(
    background_tasks: BackgroundTasks,
    question_id: int = Form(...),
    file: UploadFile = File(...),
    conn: connection = Depends(get_db_conn)
):
    """
    [면접 영상 업로드]
    """
    
    # 1. 물리적 파일 저장
    safe_filename = f"{question_id}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # 2. DB에 메타데이터 저장
    new_answer = answer_repo.create(
        conn=conn, 
        question_id=question_id, 
        video_path=file_path
    )
    
    conn.commit()
    
    # 3. 백그라운드 분석 작업 등록
    background_tasks.add_task(
        run_background_analysis, 
        new_answer['answer_id'],
        file_path
    )
    
    # 4. 결과 반환
    return new_answer


@router.post("/{answer_id}/analyze")
def retry_analysis(
    answer_id: int,
    background_tasks: BackgroundTasks,
    conn: connection = Depends(get_db_conn)
):
    """
    [재분석 요청] (관리자/디버깅용)
    """
    # 1. 답변 존재 확인
    answer = answer_repo.get_by_id(conn, answer_id)
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")
    
    # 2. 영상 파일 존재 확인
    # (answer는 딕셔너리이므로 ['video_path']로 접근)
    if not os.path.exists(answer['video_path']):
        raise HTTPException(status_code=400, detail="Video file is missing on server")

    # 3. 백그라운드 작업 다시 등록
    background_tasks.add_task(
        run_background_analysis, 
        answer['answer_id'], 
        answer['video_path']
    )
    
    return {"message": f"Re-analysis started for answer {answer_id}"}