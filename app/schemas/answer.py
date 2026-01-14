from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from enum import Enum

class AnalysisStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    DONE = "DONE"
    FAILED = "FAILED"

class AnswerResponse(BaseModel):
    """답변 영상 업로드 결과"""
    answer_id: int
    question_id: int
    video_path: str
    analysis_status: AnalysisStatus
    created_at: datetime

    class Config:
        from_attributes = True