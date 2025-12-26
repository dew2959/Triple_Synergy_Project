from typing import List
from .common import BaseAnalysisResult, AnalysisFeedback, TimeEvent

class VoiceResult(BaseAnalysisResult):
    module: str = "voice"
    
    # 핵심 지표
    score: int
    avg_wpm: int
    max_wpm: int
    silence_count: int
    avg_pitch: float
    
    # 타임라인 (침묵 구간 등) -> DB 'events_json'
    events: List[TimeEvent] = []
    
    # 상세 피드백
    feedback: AnalysisFeedback