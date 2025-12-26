from typing import List
from .common import BaseAnalysisResult, AnalysisFeedback, TimeEvent

class VisualResult(BaseAnalysisResult):
    module: str = "visual"
    
    # 핵심 지표
    score: int
    head_center_ratio: float
    
    # 타임라인 (시선 이탈 구간 등) -> DB 'events_json'
    events: List[TimeEvent] = []
    
    # 상세 피드백 -> DB 'feedback', 'good_points_json', 'bad_points_json'
    feedback: AnalysisFeedback