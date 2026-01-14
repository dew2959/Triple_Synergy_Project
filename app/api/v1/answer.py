import os
import shutil
# import uuid  <-- 제거됨
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from psycopg2.extensions import connection

from app.api.deps import get_db_conn, get_current_user
from app.repositories.answer_repo import answer_repo
from app.schemas.answer import AnswerResponse

router = APIRouter()

# 영상 저장 경로
UPLOAD_DIR = "uploads/videos"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload", response_model=AnswerResponse)
def upload_answer_video(
    question_id: int = Form(..., description="어떤 질문에 대한 답변인지 ID"),
    file: UploadFile = File(..., description="영상 파일 (mp4, webm 등)"),
    conn: connection = Depends(get_db_conn),
    current_user: dict = Depends(get_current_user)
):
    """
    [답변 영상 업로드]
    특정 질문(question_id)에 대한 답변 영상을 업로드합니다.
    """
    
    # 1. 파일명 생성 (UUID 제거 -> 유저ID + 원본파일명 사용)
    # 예: answer_q15_u1_interview_video.mp4
    # (user_id를 넣어주면 다른 유저와 파일명이 겹치지 않습니다)
    safe_filename = f"answer_q{question_id}_u{current_user['user_id']}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    # 2. 서버 로컬에 저장
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"영상 저장 실패: {e}")

    # 3. DB 저장 (Answers 테이블)
    try:
        new_answer = answer_repo.create(
            conn,
            question_id=question_id,
            video_path=file_path
        )
        conn.commit()
        return new_answer
        
    except Exception as e:
        conn.rollback()
        # 저장된 파일 삭제 (DB 실패 시 고아 파일 방지)
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"DB 저장 실패: {e}")