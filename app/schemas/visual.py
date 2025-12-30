from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from .common import AnalysisFeedback, TimeEvent

class VisualMetrics(BaseModel):
    """
    시각 분석 핵심 지표 (그래프/점수용)
    """
    score: int
    head_center_ratio: float

    events: List[TimeEvent] = Field(
        default_factory=list,
        description="시선 이탈, 고정 구간 등 타임라인 이벤트"
    )

class VisualResult(BaseModel):
    """
    시각 분석 결과 (API 응답 또는 서비스 내부 전달용)
    """
    answer_id: int
    metrics: VisualMetrics
    feedback: AnalysisFeedback


class VisualDBPayload(BaseModel):
    """
    DB answer_visual_analysis 테이블 저장용
    """
    answer_id: int

    score: int
    head_center_ratio: float

    events_json: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="TimeEvent -> dict 변환 결과"
    )

    feedback: str
    good_points_json: List[str] = Field(default_factory=list)
    bad_points_json: List[str] = Field(default_factory=list)