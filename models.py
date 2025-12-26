from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.sql import func
from database import Base # 방금 만든 database.py에서 불러옴

class Answer(Base):
    __tablename__ = "answers"

    answer_id = Column(Integer, primary_key=True, index=True)
    # Supabase는 JSON 타입을 완벽 지원하므로 그대로 사용 가능
    video_path = Column(String) 
    stt_text = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())