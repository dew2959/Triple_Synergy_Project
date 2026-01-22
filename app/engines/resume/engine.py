import json
from typing import List
from pydantic import BaseModel, Field

# 🔴 [수정] utils에서 ReportLLMClient 가져오기
from app.utils.report_llm_client import ReportLLMClient
from app.utils.prompt_utils import build_resume_question_prompt

# 출력 스키마 정의
class ResumeQuestionsOut(BaseModel):
    questions: List[str] = Field(default_factory=list)

class ResumeQuestionEngine:
    def __init__(self):
        # ReportLLMClient 사용
        self.llm_client = ReportLLMClient(model="gpt-4o-mini")

    def generate_questions(self, resume_text: str, job_role: str) -> List[str]:
        # 프롬프트 생성
        prompt = build_resume_question_prompt(job_role, resume_text)

        try:
            # 🔴 [수정] generate 호출 시 스키마(ResumeQuestionsOut) 전달
            json_str = self.llm_client.generate(prompt, response_format=ResumeQuestionsOut, temperature=0.7)
            
            # JSON 파싱
            data = json.loads(json_str)
            questions = data.get("questions", [])
            
            # 2개만 반환
            return [q.strip() for q in questions if q.strip()][:2]
            
        except Exception as e:
            print(f"❌ Resume Engine Error: {e}")
            return []

resume_question_engine = ResumeQuestionEngine()