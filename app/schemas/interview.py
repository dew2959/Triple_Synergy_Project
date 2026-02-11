# app/schemas/interview.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class TTSRequest(BaseModel):
    text: str
    voice: str = "alloy" # alloy, echo, fable, onyx, nova, shimmer 중 선택