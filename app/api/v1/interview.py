import shutil
import os
from fastapi import APIRouter, UploadFile, File, Depends, Form, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session

# 의존성 및 스키마
from app.api.deps import get_db
from app.schemas.interview import AnswerResponse

# 레포지토리 (DB 담당)
from app.repositories.answer_repo import answer_repo

# 서비스 (비즈니스 로직 & 지휘자 담당)
from app.services.analysis_service import analysis_service

router = APIRouter()

# 영상 저장 경로 설정
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# =========================================================
#  Helper Function: 백그라운드 작업 (Celery 대용)
# =========================================================
def run_background_analysis(answer_id: int, file_path: str, db: Session):
    """
    백그라운드에서 실행되는 분석 작업입니다.
    모든 로직 처리는 analysis_service에게 위임합니다.
    """
    analysis_service.run_full_analysis(db, answer_id, file_path)


# =========================================================
#  API Endpoints
# =========================================================

@router.post("/upload", response_model=AnswerResponse)
def upload_interview_video(
    background_tasks: BackgroundTasks,
    question_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    [면접 영상 업로드]
    1. 영상을 서버 스토리지에 저장합니다.
    2. DB에 '답변(Answer)' 데이터를 생성합니다. (PENDING 상태)
    3. 백그라운드에서 AI 분석을 시작하도록 예약합니다.
    4. 사용자에게는 즉시 접수 완료 응답(AnswerResponse)을 보냅니다.
    """
    
    # 1. 물리적 파일 저장 (Local Storage)
    # 파일명 충돌 방지를 위해 question_id를 prefix로 붙임
    safe_filename = f"{question_id}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # 2. DB에 메타데이터 저장 (Repository 이용)
    # 이때 answer_repo 내부에서 status='PENDING'으로 생성됨
    new_answer = answer_repo.create(
        db=db, 
        question_id=question_id, 
        video_path=file_path
    )
    
    # 3. 백그라운드 분석 작업 등록 (비동기 실행)
    # 주의: db 세션을 넘길 때 스레드 안전성을 고려해야 하지만, 
    # 현재 단계(Prototype)에서는 그대로 전달합니다.
    background_tasks.add_task(
        run_background_analysis, 
        new_answer.answer_id, 
        file_path, 
        db
    )
    
    # 4. 결과 반환 (Pydantic Schema가 자동으로 변환)
    return new_answer


@router.post("/{answer_id}/analyze")
def retry_analysis(
    answer_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    [재분석 요청] (관리자/디버깅용)
    분석이 실패했거나 멈췄을 때, 강제로 다시 분석을 돌립니다.
    """
    # 1. 답변 존재 확인
    answer = answer_repo.get_by_id(db, answer_id)
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")
    
    # 2. 영상 파일 존재 확인
    if not os.path.exists(answer.video_path):
        raise HTTPException(status_code=400, detail="Video file is missing on server")

    # 3. 백그라운드 작업 다시 등록
    background_tasks.add_task(
        run_background_analysis, 
        answer.answer_id, 
        answer.video_path,
        db
    )
    
    return {"message": f"Re-analysis started for answer {answer_id}"}