from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from .common import AnalysisFeedback


# 1. Content Metrics
class ContentMetrics(BaseModel):
    """
    내용(텍스트) 분석 핵심 지표
    - LLM 평가 점수 위주
    """
    logic_score: int = Field(..., description="논리성/구조 점수 (1~5)")
    job_fit_score: int = Field(..., description="직무 적합도 점수 (0~100)")
    filler_count: int = Field(..., description="필러 단어 사용 횟수")

    keywords: List[str] = Field(
        default_factory=list,
        description="핵심 키워드 (직무/역량 중심)"
    )


# 2. API / Service 결과용
class ContentResult(BaseModel):
    """
    내용 분석 결과 (API 응답 / 서비스 내부 전달용)
    """
    answer_id: int
    metrics: ContentMetrics
    feedback: AnalysisFeedback

    summarized_text: Optional[str] = Field(
        default=None,
        description="사용자 답변 요약"
    )

    model_answer: Optional[str] = Field(
        default=None,
        description="개선된 모범 답변 (LLM 생성)"
    )

# 3. DB 저장 Payload
class ContentDBPayload(BaseModel):
    """
    answer_content_analysis 테이블 저장용
    """
    answer_id: int

    logic_score: int
    job_fit_score: int
    filler_count: int

    keywords_json: List[str] = Field(default_factory=list)

    feedback: str
    model_answer: Optional[str] = None
    summarized_text: Optional[str] = None
