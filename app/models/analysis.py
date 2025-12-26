from sqlalchemy import Column, BigInteger, Integer, Float, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.db import Base

class AnswerVisualAnalysis(Base):
    __tablename__ = "answer_visual_analysis"

    id = Column(BigInteger, primary_key=True, index=True)
    answer_id = Column(BigInteger, ForeignKey("answers.answer_id", ondelete="CASCADE"), nullable=False)
    
    score = Column(Integer)
    head_center_ratio = Column(Float)
    
    feedback = Column(Text)
    good_points_json = Column(JSON) # Postgres JSONB 대응
    bad_points_json = Column(JSON)

    answer = relationship("Answer", back_populates="visual_analysis")

class AnswerVoiceAnalysis(Base):
    __tablename__ = "answer_voice_analysis"

    id = Column(BigInteger, primary_key=True, index=True)
    answer_id = Column(BigInteger, ForeignKey("answers.answer_id", ondelete="CASCADE"), nullable=False)
    
    score = Column(Integer)
    avg_wpm = Column(Integer)
    max_wpm = Column(Integer)
    silence_count = Column(Integer)
    avg_pitch = Column(Float)
    
    feedback = Column(Text)
    good_points_json = Column(JSON)
    bad_points_json = Column(JSON)

    answer = relationship("Answer", back_populates="voice_analysis")

class AnswerContentAnalysis(Base):
    __tablename__ = "answer_content_analysis"

    id = Column(BigInteger, primary_key=True, index=True)
    answer_id = Column(BigInteger, ForeignKey("answers.answer_id", ondelete="CASCADE"), nullable=False)
    
    logic_score = Column(Integer)
    job_fit_score = Column(Integer)
    time_management_score = Column(Integer)
    
    feedback = Column(Text)
    model_answer = Column(Text)
    keywords_json = Column(JSON)

    answer = relationship("Answer", back_populates="content_analysis")

class FinalReport(Base):
    __tablename__ = "final_reports"

    report_id = Column(BigInteger, primary_key=True, index=True)
    session_id = Column(BigInteger, ForeignKey("interview_sessions.session_id", ondelete="CASCADE"), nullable=False)
    
    total_score = Column(Integer)
    summary_headline = Column(Text)
    overall_feedback = Column(Text)
    
    avg_visual_score = Column(Integer)
    avg_voice_score = Column(Integer)
    avg_content_score = Column(Integer)
    
    visual_strengths_json = Column(JSON)
    visual_weaknesses_json = Column(JSON)
    voice_strengths_json = Column(JSON)
    voice_weaknesses_json = Column(JSON)
    content_strengths_json = Column(JSON)
    content_weaknesses_json = Column(JSON)
    
    action_plans_json = Column(JSON)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("InterviewSession", back_populates="final_report")