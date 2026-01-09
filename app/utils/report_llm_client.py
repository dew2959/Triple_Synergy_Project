from typing import List, Optional
from pydantic import BaseModel, Field
from openai import OpenAI

from app.core.config import Settings  # ✅ 경로가 다르면 여기만 수정


class ActionPlanItem(BaseModel):
    title: str
    description: str


class FinalReportLLMOut(BaseModel):
    summary_headline: str
    overall_feedback: str

    visual_summary: Optional[str] = None
    voice_summary: Optional[str] = None
    content_summary: Optional[str] = None

    visual_strengths_json: List[str] = Field(default_factory=list)
    visual_weaknesses_json: List[str] = Field(default_factory=list)

    voice_strengths_json: List[str] = Field(default_factory=list)
    voice_weaknesses_json: List[str] = Field(default_factory=list)

    content_strengths_json: List[str] = Field(default_factory=list)
    content_weaknesses_json: List[str] = Field(default_factory=list)

    action_plans_json: List[ActionPlanItem] = Field(default_factory=list)


class ReportLLMClient:
    def __init__(self, model: str = "gpt-4o-mini"):
        if not Settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is empty. Check .env loading and settings.")
        self.client = OpenAI(api_key=Settings.OPENAI_API_KEY)
        self.model = model

    def generate(self, prompt: str, temperature: float = 0.2) -> str:
        """
        FinalReportService가 기대하는 형태: JSON 문자열
        """
        resp = self.client.responses.parse(
            model=self.model,
            input=[
                {"role": "system", "content": "Return ONLY valid JSON matching the schema. No markdown."},
                {"role": "user", "content": prompt},
            ],
            text_format=FinalReportLLMOut,
            temperature=temperature,
        )
        return resp.output_parsed.model_dump_json()
