# app/schemas/interview.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# [응답용] 프론트엔드에게 돌려줄 데이터 형식
class AnswerResponse(BaseModel):
    answer_id: int
    video_path: str
    created_at: datetime
    
    # ORM 객체(DB 모델)를 Pydantic 모델로 변환 허용
    class Config:
        from_attributes = True