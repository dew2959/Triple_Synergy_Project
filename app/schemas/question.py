from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

# DB의 ENUM과 일치시키는 파이썬 Enum
class QuestionCategory(str, Enum):
    GENERAL = "GENERAL"
    JOB_FIT = "JOB_FIT"
    TECHNICAL = "TECHNICAL"
    PROJECT = "PROJECT"

class QuestionCreate(BaseModel):
    """질문 생성 요청"""
    session_id: int = Field(..., description="연결된 세션 ID")
    content: str = Field(..., description="질문 내용")
    category: QuestionCategory = Field(default=QuestionCategory.GENERAL, description="질문 카테고리")
    order_index: int = Field(default=1, description="질문 순서")

class QuestionResponse(QuestionCreate):
    """질문 응답"""
    question_id: int
    created_at: datetime

    class Config:
        from_attributes = True