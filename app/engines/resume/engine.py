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

from app.schemas.resume import ResumeQuestionsOut

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
        ("system", """
        너는 10년 차 시니어 기술 면접관이다.
        너의 임무는 오직 제공된 이력서(resume_text) 안의 정보에 근거해서만 면접 질문을 만드는 것이다.

        [핵심 규칙 - 매우 중요]
        1) 이력서에 없는 사실을 절대 가정하지 마라.
        - 회사 경력/연차/직무 경험이 명시되지 않으면 '경력'을 전제로 묻지 마라.
        - 프로젝트/기술스택/역할이 명시되지 않으면 특정 이름/도구/성과를 전제로 묻지 마라.
        2) 질문은 반드시 이력서에 적힌 근거(evidence)를 직접 참조해 만들어라.
        3) 이력서 정보가 부족하면, 먼저 사실을 확인하는 '확인 질문'을 하라.
        - 예: "이력서에 프로젝트가 구체적으로 적혀 있지 않습니다. 최근 6개월 내 진행한 프로젝트가 있나요?"
        4) 질문은 직무(job_role) 검증이 목적이며, 가능한 한 구체적으로:
        - 본인 기여/역할, 의사결정 이유, 트레이드오프, 실패/개선, 재현 가능성, 검증 방법을 묻는다.
        5) 한국어로, 질문은 총 2개만 생성한다.

        [금지 예시]
        - "이전 회사에서 어떤 업무를 했나요?" (이력서에 회사 경력 없음)
        - "OO 프로젝트에서 어떤 성과를 냈나요?" (이력서에 OO 프로젝트 없음)
        """),
        ("human", """
        [지원 직무]
        {job_role}

        [이력서 내용]
        {resume_text}

        요청:
        - 면접 질문 2개를 생성해줘.
        - 이력서에 프로젝트가 없으면, 2개 중 최소 1개는 정보 확인 질문으로 만들어.
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