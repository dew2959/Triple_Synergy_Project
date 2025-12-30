from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class StrengthWeakness(BaseModel):
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)

class ModuleScoreSummary(BaseModel):
    avg_score: int
    summary: Optional[str] = None

class ActionPlan(BaseModel):  #LLM 생성
    title: str
    description: str


class FinalReportResult(BaseModel):
    """
    최종 종합 리포트 (API Response)
    """
    session_id: int

    # ===== 전체 점수 =====
    total_score: int
    summary_headline: str
    overall_feedback: str

    # ===== 모듈별 점수 =====
    visual: ModuleScoreSummary
    voice: ModuleScoreSummary
    content: ModuleScoreSummary

    # ===== 강점 / 약점 =====
    visual_points: StrengthWeakness
    voice_points: StrengthWeakness
    content_points: StrengthWeakness

    # ===== 액션 플랜 =====
    action_plans: List[ActionPlan] = Field(default_factory=list)

    created_at: Optional[str] = None



class FinalReportDBPayload(BaseModel):
    """
    final_reports 테이블 저장용
    """
    session_id: int

    total_score: int
    summary_headline: str
    overall_feedback: str

    avg_visual_score: int
    avg_voice_score: int
    avg_content_score: int

    visual_strengths_json: List[str] = Field(default_factory=list)
    visual_weaknesses_json: List[str] = Field(default_factory=list)

    voice_strengths_json: List[str] = Field(default_factory=list)
    voice_weaknesses_json: List[str] = Field(default_factory=list)

    content_strengths_json: List[str] = Field(default_factory=list)
    content_weaknesses_json: List[str] = Field(default_factory=list)

    action_plans_json: List[dict] = Field(default_factory=list)
