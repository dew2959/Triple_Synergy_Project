from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

class ResumeUploadResponse(BaseModel):
    resume_id: int
    parsed_text: Optional[str]

class ResumeView(BaseModel):
    resume_id: int
    file_path: str
    created_at: datetime
