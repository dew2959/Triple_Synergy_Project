import json
import os
from typing import List

# 기존에 만드신 OpenAI Adapter 재사용 (없으면 import 경로 수정)
from app.services.final_report_service import OpenAIClientAdapter 

class ResumeQuestionEngine:
    def __init__(self):
        self.llm = OpenAIClientAdapter()

    def generate_questions(self, resume_text: str, job_role: str) -> List[str]:
        """
        이력서 내용을 바탕으로 심층 면접 질문 2개를 생성합니다.
        """
        prompt = f"""
        너는 전문 면접관이다. 지원자의 이력서 내용을 바탕으로 직무 역량과 프로젝트 경험을 검증할 수 있는 날카로운 면접 질문 2개를 생성하라.

        [지원 직무]
        {job_role}

        [이력서 내용]
        {resume_text}

        [규칙]
        1. 질문은 한국어로 작성할 것.
        2. 이력서의 구체적인 프로젝트나 경험을 언급하며 질문할 것.
        3. 반드시 JSON 리스트 포맷으로 출력할 것. 예: ["질문1", "질문2"]
        4. 오직 JSON만 출력할 것.
        """

        try:
            response = self.llm.generate(prompt, temperature=0.7)
            questions = json.loads(response)
            
            # 리스트 형태인지 확인하고 2개만 자름
            if isinstance(questions, list):
                return questions[:2]
            elif isinstance(questions, dict) and "questions" in questions:
                return questions["questions"][:2]
            else:
                return [] # 파싱 실패 시 빈 리스트
                
        except Exception as e:
            print(f"❌ Resume Engine Error: {e}")
            return [] # 에러 시 빈 리스트 (Service에서 랜덤 질문으로 대체)

resume_question_engine = ResumeQuestionEngine()