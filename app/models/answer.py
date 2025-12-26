# app/models/answer.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey # [1] ForeignKey 추가
from sqlalchemy.sql import func
from app.core.db import Base

class Answer(Base):
    __tablename__ = "answers"

    answer_id = Column(Integer, primary_key=True, index=True)
    
    # [2] 이 줄이 빠져 있어서 에러가 난 겁니다! 추가해주세요.
    # (nullable=False는 DB 설정에 맞춤)
    question_id = Column(Integer, nullable=False) 
    
    video_path = Column(String, nullable=True)
    audio_path = Column(String, nullable=True)
    stt_text = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())