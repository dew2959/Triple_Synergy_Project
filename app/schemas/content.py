from typing import List
from .common import BaseAnalysisResult, AnalysisFeedback

class ContentResult(BaseAnalysisResult):
    module: str = "content"
    
    # 핵심 지표 (3가지 평가 요소)
    logic_score: int
    job_fit_score: int
    time_management_score: int
    
    # 키워드 분석 -> DB 'keywords_json'
    keywords: List[str] = []
    
    # 상세 피드백
    # feedback.summary -> DB 'feedback'
    # feedback.script_modified -> DB 'model_answer'
    feedback: AnalysisFeedback