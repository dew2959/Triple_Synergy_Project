from typing import List, Dict, Any
from pydantic import BaseModel, Field
from .common import AnalysisFeedback, TimeEvent

class VoiceMetrics(BaseModel):
    """
    음성 분석 핵심 지표 (그래프/점수용)
    """
    score: int

    wpm: int
    avg_pitch: float
    max_pitch: float

    silence_count: int
    avg_silence_length: float

    silence_events: List[TimeEvent] = Field(
        default_factory=list,
        description="침묵 구간 타임라인 이벤트"
    )

class VoiceResult(BaseModel):
    """
    음성 분석 결과 (API 응답 / 서비스 내부 전달용)
    """
    answer_id: int
    metrics: VoiceMetrics
    feedback: AnalysisFeedback


class VoiceDBPayload(BaseModel):
    """
    answer_voice_analysis 테이블 저장용
    """
    answer_id: int

    score: int

    avg_wpm: int
    max_wpm: int

    silence_count: int
    avg_silence_length: float

    avg_pitch: float
    max_pitch: float

    silence_timeline_json: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="TimeEvent -> dict 변환 결과"
    )

    feedback: str
    good_points_json: List[str] = Field(default_factory=list)
    bad_points_json: List[str] = Field(default_factory=list)