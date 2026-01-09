from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
from datetime import datetime

# 1. 개별 모듈 점수 요약
class ModuleScoreSummary(BaseModel):
    avg_score: int
    summary: Optional[str] = None

# 2. 강점/약점 리스트
class StrengthWeakness(BaseModel):
    strengths: List[str] = []
    weaknesses: List[str] = []

# 3. 개선 계획 (Action Plan)
class ActionPlan(BaseModel):
    title: str
    description: str

# 4. 서비스 결과 반환용 (API 응답)
class FinalReportResult(BaseModel):
    session_id: int
    total_score: int
    summary_headline: str
    overall_feedback: str

    visual: ModuleScoreSummary
    voice: ModuleScoreSummary
    content: ModuleScoreSummary

    visual_points: StrengthWeakness
    voice_points: StrengthWeakness
    content_points: StrengthWeakness

    action_plans: List[ActionPlan]
    created_at: Optional[str] = None

# 5. DB 저장용 Payload (Repository로 전달)
class FinalReportDBPayload(BaseModel):
    session_id: int
    total_score: int
    summary_headline: str
    overall_feedback: str

    avg_visual_score: int
    avg_voice_score: int
    avg_content_score: int

    visual_strengths_json: List[str] = []
    visual_weaknesses_json: List[str] = []
    voice_strengths_json: List[str] = []
    voice_weaknesses_json: List[str] = []
    content_strengths_json: List[str] = []
    content_weaknesses_json: List[str] = []

    action_plans_json: List[Dict[str, str]] = []