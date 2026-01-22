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



# LLM이 출력할 구조 정의 (LangChain용)
class ActionPlanItem(BaseModel):
    title: str = Field(description="액션 플랜 제목")
    description: str = Field(description="구체적인 실행 방법")

class FinalReportLLMOut(BaseModel):
    summary_headline: str = Field(description="면접 전체를 관통하는 한 줄 요약")
    overall_feedback: str = Field(description="면접 전체에 대한 종합 피드백 (3~4문장)")

    visual_summary: Optional[str] = Field(None, description="비주얼(표정/자세) 요약")
    voice_summary: Optional[str] = Field(None, description="음성(목소리/빠르기) 요약")
    content_summary: Optional[str] = Field(None, description="내용(논리/직무) 요약")

    visual_strengths_json: List[str] = Field(description="비주얼 강점 2~4개")
    visual_weaknesses_json: List[str] = Field(description="비주얼 약점 2~4개")

    voice_strengths_json: List[str] = Field(description="음성 강점 2~4개")
    voice_weaknesses_json: List[str] = Field(description="음성 약점 2~4개")

    content_strengths_json: List[str] = Field(description="내용 강점 2~4개")
    content_weaknesses_json: List[str] = Field(description="내용 약점 2~4개")

    action_plans_json: List[ActionPlanItem] = Field(description="개선 행동 계획 3~7개")