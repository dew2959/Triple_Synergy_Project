from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum

# DB의 ENUM과 일치시키는 파이썬 Enum
class SessionStatus(str, Enum):
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    ANALYZING = "ANALYZING"
    COMPLETED = "COMPLETED"

class QuestionItem(BaseModel):
    question_id: int
    content: str
    category: str
    order_index: int

    class Config:
        from_attributes = True


class SessionCreate(BaseModel):
    """
    [세션 생성 요청]
    사용자는 '어떤 이력서'로 면접을 볼 것인지만 선택하면 됩니다.
    나머지 정보(직무, 회사 등)는 백엔드에서 이력서를 보고 자동으로 채웁니다.
    """
    resume_id: Optional[int] = Field(None, description="이력서 ID (생략 시 최신 이력서 사용)")

class SessionResponse(BaseModel):
    """
    [세션 응답]
    생성된 세션의 상태와 메타데이터를 반환합니다.
    """
    session_id: int
    user_id: int
    resume_id: Optional[int]
    
    # 이력서에서 복사해온 정보들
    job_role: Optional[str] = Field(None, description="지원 직무")
    company_name: Optional[str] = Field(None, description="목표 회사")
    
    status: SessionStatus
    created_at: datetime

    class Config:
        from_attributes = True
