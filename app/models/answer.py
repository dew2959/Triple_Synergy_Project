from sqlalchemy import Column, Integer, String, Text, DateTime, func
from app.core.db import Base # 위치 변경됨

class Answer(Base):
    __tablename__ = "answers"

    answer_id = Column(Integer, primary_key=True, index=True)
    video_path = Column(String, nullable=True)
    audio_path = Column(String, nullable=True)
    stt_text = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())