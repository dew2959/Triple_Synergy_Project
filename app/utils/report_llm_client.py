from typing import Type, TypeVar
from pydantic import BaseModel
from openai import OpenAI
from app.core.config import settings

# 제네릭 타입 정의 (Pydantic 모델을 동적으로 받기 위함)
T = TypeVar("T", bound=BaseModel)

class ReportLLMClient:
    def __init__(self, model: str = "gpt-4o-mini"):
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is empty. Check .env loading and settings.")
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = model

    def generate(self, prompt: str, response_format: Type[T], temperature: float = 0.2) -> str:
        """
        OpenAI의 Structured Output 기능을 사용하여
        지정된 Pydantic 모델(response_format) 스키마에 맞는 JSON을 반환합니다.
        """
        try:
            # client.beta.chat.completions.parse 사용 (OpenAI SDK v1.x 최신 표준)
            completion = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant. Return ONLY valid JSON matching the schema. No markdown."},
                    {"role": "user", "content": prompt},
                ],
                response_format=response_format,
                temperature=temperature,
            )
            
            # 파싱된 객체를 다시 JSON 문자열로 변환하여 반환
            # (서비스 계층에서 다시 객체로 변환하거나 DB에 저장하기 용이하게)
            return completion.choices[0].message.parsed.model_dump_json()
            
        except Exception as e:
            print(f"❌ LLM Generation Error: {e}")
            # 에러 발생 시 빈 JSON 객체 반환 (혹은 예외를 다시 던짐)
            return "{}"