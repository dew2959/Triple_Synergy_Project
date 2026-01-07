# app/schemas/interview.py
from pydantic import BaseModel
from datetime import datetime

class AnswerResponse(BaseModel):
    answer_id: int
    video_path: str
    created_at: datetime
    
    class Config:
        from_attributes = True