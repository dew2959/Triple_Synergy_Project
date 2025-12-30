from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.models.enums import SessionStatus, QuestionCategory

# [질문 응답] 프론트엔드에 "이거 물어보세요" 하고 줄 때
class QuestionResponse(BaseModel):
    question_id: int
    content: str
    order_index: int
    category: QuestionCategory

    class Config:
        from_attributes = True

# [세션 시작 요청] (Input)
class SessionCreate(BaseModel):
    user_id: int # 나중엔 토큰에서 자동 추출
    resume_id: Optional[int] = None # 이력서 기반 면접일 경우
    job_role: str = "Backend Developer"
    company_name: str = "Tech Corp"

# [세션 정보 응답] (Output)
class SessionResponse(BaseModel):
    session_id: int
    status: SessionStatus
    job_role: str
    created_at: datetime
    
    # 현재 세션의 질문 목록 포함 (선택)
    questions: List[QuestionResponse] = []

    class Config:
        from_attributes = True