from typing import List
from pydantic import BaseModel, Field
from app.core.config import settings
from openai import OpenAI
from app.utils.prompt_utils import sanitize_text, filter_or_raise

class ResumeQuestionsOut(BaseModel):
    questions: List[str] = Field(default_factory=list)

class ResumeQuestionEngine:
    def __init__(self, model: str = "gpt-4o-mini"):
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is empty")
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = model

    def generate_questions(self, resume_text: str, job_role: str) -> List[str]:
        safe_resume = sanitize_text(resume_text)
        safe_role = sanitize_text(job_role)
        filter_or_raise(safe_resume, where="resume.text")
        filter_or_raise(safe_role, where="resume.job_role")

        prompt = f"""
너는 전문 면접관이다. 지원자의 이력서 내용을 바탕으로 직무 역량과 프로젝트 경험을 검증할 수 있는 날카로운 면접 질문 2개를 생성하라.

[지원 직무]
{safe_role}

[이력서 내용]
{safe_resume}

[출력 규칙]
- 반드시 아래 JSON 객체 스키마로만 출력:
{{"questions": ["질문1", "질문2"]}}
- 오직 JSON만 출력
""".strip()

        try:
            resp = self.client.responses.parse(
                model=self.model,
                input=[
                    {"role": "system", "content": "Return ONLY valid JSON. No markdown."},
                    {"role": "user", "content": prompt},
                ],
                text_format=ResumeQuestionsOut,
                temperature=0.7,
            )
            out = resp.output_parsed
            qs = [q.strip() for q in (out.questions or []) if q and q.strip()]
            return qs[:2]
        except Exception as e:
            print(f"❌ Resume Engine Error: {e}")
            return []
