# app/schemas/interview.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class AnswerResponse(BaseModel):
    answer_id: int
    video_path: str
    created_at: datetime
    
    class Config:
        from_attributes = True
        
class RetryAnalysisResponse(BaseModel):
    message: str


class TTSRequest(BaseModel):
    text: str
    voice: str = "alloy" # alloy, echo, fable, onyx, nova, shimmer 중 선택