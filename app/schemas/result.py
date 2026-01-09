from typing import List, Optional, Dict, Any
from pydantic import BaseModel

# ==========================================
# 1. 비주얼 분석 응답 (VisualResultResponse)
# ==========================================
class VisualResultResponse(BaseModel):
    """
    answer_visual_analysis 테이블 구조와 1:1 매핑
    """
    id: int
    answer_id: int
    score: Optional[int] = 0
    head_center_ratio: Optional[float] = 0.0
    feedback: Optional[str] = None
    good_points_json: Optional[List[str]] = []
    bad_points_json: Optional[List[str]] = []

# ==========================================
# 2. 음성 분석 응답 (VoiceResultResponse)
# ==========================================
class VoiceResultResponse(BaseModel):
    """
    answer_voice_analysis 테이블 구조와 1:1 매핑
    """
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

# ==========================================
# 3. 내용 분석 응답 (ContentResultResponse)
# ==========================================
class ContentResultResponse(BaseModel):
    """
    answer_content_analysis 테이블 구조와 1:1 매핑
    
    [주의] SQL 스키마에 'score'와 'filler_count' 컬럼이 없으므로 제거했습니다.
    필요하다면 프론트엔드에서 logic/job_fit/time 점수의 평균을 계산해 사용하거나,
    SQL에 해당 컬럼을 추가해야 합니다.
    """
    id: int
    answer_id: int
    
    # DB에 있는 3가지 세부 점수
    logic_score: Optional[int] = 0
    job_fit_score: Optional[int] = 0
    time_management_score: Optional[int] = 0
    
    feedback: Optional[str] = None
    model_answer: Optional[str] = None
    keywords_json: Optional[List[str]] = []