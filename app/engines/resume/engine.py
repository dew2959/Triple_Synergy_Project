import os
from typing import List
from pydantic import BaseModel, Field

# LangChain 관련 임포트
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

# 기존 유틸 (전처리용함수는 유지)
from app.utils.prompt_utils import sanitize_text
from app.core.config import settings

# 1. LLM이 반환해야 할 데이터 구조 정의 (Pydantic)
class ResumeQuestionsOut(BaseModel):
    questions: List[str] = Field(
        description="이력서를 보고 생성한 날카로운 면접 질문 2개",
        min_items=2,
        max_items=2
    )

class ResumeQuestionEngine:
    def __init__(self):
        # 2. ChatOpenAI 모델 초기화 (기존 ReportLLMClient 대체)
        self.llm = ChatOpenAI(
            model="gpt-4o",  # 또는 gpt-3.5-turbo
            api_key=settings.OPENAI_API_KEY,
            temperature=0.7,
        )

    def generate_questions(self, resume_text: str, job_role: str) -> List[str]:
        """
        LangChain을 사용하여 이력서 기반 질문 2개를 생성합니다.
        """
        
        # 3. 이력서 텍스트 전처리 (기존 유틸 사용)
        clean_resume = sanitize_text(resume_text)

        # 4. 프롬프트 템플릿 정의 (PromptUtils 대체)
        # 시스템 메시지와 사용자 메시지를 구조적으로 분리
        prompt = ChatPromptTemplate.from_messages([
            ("system", "너는 10년 차 시니어 기술 면접관이다. 지원자의 이력서를 분석하여 직무 적합성을 검증할 수 있는 예리한 질문을 한다."),
            ("human", """
            [지원 직무]
            {job_role}

            [이력서 내용]
            {resume_text}

            위 내용을 바탕으로 면접 질문 2개를 한국어로 생성해줘.
            구체적인 프로젝트 경험이나 기술 스택을 언급하며 질문해야 해.
            """),
        ])

        # 5. 체인 연결 (Prompt -> LLM -> Structured Output)
        # with_structured_output을 쓰면 JSON 파싱을 자동으로 해줍니다.
        chain = prompt | self.llm.with_structured_output(ResumeQuestionsOut)

        try:
            # 6. 실행 (Invoke)
            result: ResumeQuestionsOut = chain.invoke({
                "job_role": job_role,
                "resume_text": clean_resume
            })
            
            # 결과 반환
            return result.questions

        except Exception as e:
            print(f"❌ [LangChain Error] Resume Question Generation Failed: {e}")
            # 실패 시 빈 리스트 반환 (Service에서 랜덤 질문으로 대체됨)
            return []

# 싱글톤 인스턴스
resume_question_engine = ResumeQuestionEngine()