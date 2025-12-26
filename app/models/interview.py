from sqlalchemy import Column, BigInteger, Integer, Text, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.db import Base
from app.models.enums import SessionStatus, QuestionCategory, AnswerAnalysisStatus, PoolCategory

class DefaultQuestionPool(Base):
    __tablename__ = "default_question_pool"

    pool_id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    category = Column(Enum(PoolCategory), nullable=False)
    fixed_order = Column(Integer)

class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    session_id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    resume_id = Column(BigInteger, ForeignKey("resumes.resume_id", ondelete="SET NULL"), nullable=True)
    
    job_role = Column(Text)
    company_name = Column(Text)
    status = Column(Enum(SessionStatus), default=SessionStatus.READY)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="sessions")
    resume = relationship("Resume", back_populates="sessions")
    questions = relationship("Question", back_populates="session", cascade="all, delete-orphan")
    final_report = relationship("FinalReport", back_populates="session", uselist=False)

class Question(Base):
    __tablename__ = "questions"

    question_id = Column(BigInteger, primary_key=True, index=True)
    session_id = Column(BigInteger, ForeignKey("interview_sessions.session_id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(Enum(QuestionCategory), default=QuestionCategory.GENERAL)
    order_index = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("InterviewSession", back_populates="questions")
    answers = relationship("Answer", back_populates="question", cascade="all, delete-orphan")

class Answer(Base):
    __tablename__ = "answers"

    answer_id = Column(BigInteger, primary_key=True, index=True)
    question_id = Column(BigInteger, ForeignKey("questions.question_id", ondelete="CASCADE"), nullable=False)
    
    video_path = Column(Text)
    audio_path = Column(Text)
    stt_text = Column(Text)
    duration = Column(Integer)
    analysis_status = Column(Enum(AnswerAnalysisStatus), default=AnswerAnalysisStatus.PENDING)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    question = relationship("Question", back_populates="answers")
    
    # Analysis Relationships (1:1)
    visual_analysis = relationship("AnswerVisualAnalysis", back_populates="answer", uselist=False)
    voice_analysis = relationship("AnswerVoiceAnalysis", back_populates="answer", uselist=False)
    content_analysis = relationship("AnswerContentAnalysis", back_populates="answer", uselist=False)