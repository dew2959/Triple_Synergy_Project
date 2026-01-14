from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

# 기존 스키마들 import (같은 파일 내에 있다면 생략 가능)
from app.schemas.report import FinalReportResult 

# -----------------------------------------------------
# [기존 코드 유지] 개별 분석 결과 스키마들
# -----------------------------------------------------
class VisualResultResponse(BaseModel):
    id: int
    answer_id: int
    score: Optional[int] = 0
    head_center_ratio: Optional[float] = 0.0
    feedback: Optional[str] = None
    good_points_json: Optional[List[str]] = []
    bad_points_json: Optional[List[str]] = []

class VoiceResultResponse(BaseModel):
    id: int
    answer_id: int
    score: Optional[int] = 0
    avg_wpm: Optional[int] = 0
    max_wpm: Optional[int] = 0
    silence_count: Optional[int] = 0
    avg_pitch: Optional[float] = 0.0
    feedback: Optional[str] = None
    good_points_json: Optional[List[str]] = []
    bad_points_json: Optional[List[str]] = []

class ContentResultResponse(BaseModel):
    id: int
    answer_id: int
    logic_score: Optional[int] = 0
    job_fit_score: Optional[int] = 0
    time_management_score: Optional[int] = 0
    feedback: Optional[str] = None
    model_answer: Optional[str] = None
    keywords_json: Optional[List[str]] = []


# -----------------------------------------------------
# [NEW] 통합 응답용 스키마
# -----------------------------------------------------

# 1. 질문 + 답변 + 3가지 분석 결과를 하나로 묶음
class AnswerFullResult(BaseModel):
    question_id: int
    question_content: str
    answer_id: int
    video_path: Optional[str]
    created_at: datetime
    
    # 분석 결과 (아직 분석 안 됐으면 None일 수 있음)
    visual: Optional[VisualResultResponse] = None
    voice: Optional[VoiceResultResponse] = None
    content: Optional[ContentResultResponse] = None

# 2. 최종 리포트 + 위 답변 리스트를 묶음


class SessionFullResultResponse(BaseModel):
    session_id: int
    # 최종 리포트 (아직 생성 안 됐으면 None)
    final_report: Optional[FinalReportResult] = None
    # 질문별 상세 분석 결과 리스트
    answers: List[AnswerFullResult] = []