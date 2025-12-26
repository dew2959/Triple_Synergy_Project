import shutil
import os
from fastapi import APIRouter, UploadFile, File, Depends, Form # [1] Form 추가 import
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.interview import AnswerResponse
from app.repositories.answer_repo import answer_repo

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload", response_model=AnswerResponse)
def upload_interview_video(
    question_id: int = Form(...), # [2] Swagger에서 입력받도록 추가
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # 1. 파일 저장
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # 2. DB 저장 (question_id 함께 전달)
    new_answer = answer_repo.create(
        db=db, 
        question_id=question_id, # [3] Repository로 전달
        video_path=file_path
    )
    
    return new_answer