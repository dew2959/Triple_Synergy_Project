from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

# 1. 공통 하위 컴포넌트 (부품)
class TimeEvent(BaseModel):
    """
    타임라인 이벤트 (그래프 시각화용)
    예: 침묵 구간(0~1.5초), 시선 이탈(12~14초)
    """
    type: str       # 예: "silence", "eye_off", "filler_word"
    start: float    # 시작 시간 (초)
    end: float      # 끝 시간 (초)
    duration: float # 지속 시간
    value: Optional[Any] = None # (선택) 해당 구간의 구체적 수치

class AnalysisFeedback(BaseModel):
    """
    피드백 데이터 구조
    """
    summary: str = ""                # (필수) 한 줄 총평 -> DB 'feedback' 컬럼
    good_points: List[str] = []      # (선택) 잘한 점 -> DB 'good_points_json'
    bad_points: List[str] = []       # (선택) 아쉬운 점 -> DB 'bad_points_json'
    script_modified: Optional[str] = None # (Content용) 모범 답안 -> DB 'model_answer'


# 2. 분석 결과 기본 껍데기 (Base)

class BaseAnalysisResult(BaseModel):
    """모든 분석 결과의 부모 클래스"""
    module: str             # "visual", "voice", "content"
    session_id : str
    answer_id: str          # DB PK
    metrics: Dict[str, Any] = Field(default_factory=dict) # 핵심 지표
    feedback: AnalysisFeedback = Field(default_factory=AnalysisFeedback) # 위에서 정의한 클래스 재사용
    db: Dict[str, Any] = Field(default_factory=dict) # DB 저장용 추가 데이터가 있다면 사용
    error_msg: Optional[str] = None
