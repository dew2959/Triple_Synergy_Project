# app/utils/prompt_utils.py (기존 파일에 추가)

import re
import json
from typing import Any, Dict, List

_RE_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_RE_PHONE = re.compile(r"\b01[016789]-?\d{3,4}-?\d{4}\b")

# ⚠️ 팀 합의된 최소 패턴만 넣는 걸 추천 (너무 방대하게 넣지 말기)
_BANNED = [
    # re.compile(r"..."),  # 예: 명백한 욕설/혐오 키워드 패턴
]

_MAX_CHARS = 8000  # 필요하면 조정

def sanitize_text(text: str) -> str:
    t = (text or "").strip()
    t = _RE_EMAIL.sub("[REDACTED_EMAIL]", t)
    t = _RE_PHONE.sub("[REDACTED_PHONE]", t)
    if len(t) > _MAX_CHARS:
        t = t[:_MAX_CHARS] + "\n...[TRUNCATED]..."
    return t

def filter_or_raise(text: str, where: str = "prompt") -> None:
    for pat in _BANNED:
        if pat.search(text):
            raise ValueError(f"PromptBlocked: banned content in {where}")

def safe_json(obj: Any) -> str:
    # dict를 prompt에 넣을 때 repr 말고 JSON 문자열로 넣어야 품질이 안정적
    return json.dumps(obj, ensure_ascii=False, default=str)

def build_content_messages(question_text: str, answer_text: str) -> List[Dict[str, str]]:
    system_prompt = """
너는 10년 차 시니어 면접관이다.
지원자의 답변을 분석해 아래 JSON 형식으로만 응답하라.
설명/사족 없이 오직 JSON만 반환하라.

{
  "logic_score": (0~100 정수),
  "job_fit_score": (0~100 정수, 질문 의도/직무 부합),
  "time_management_score": (0~100 정수, 길이/전개 적절성),
  "feedback": "한글 3문장 이내의 구체 피드백",
  "recommended_keywords": ["키워드1", "키워드2", ...],
  "model_answer": "다듬어진 모범 답안 예시(짧게)"
}
""".strip()

    user_prompt = f"""
[질문]
{question_text.strip()}

[지원자 답변]
{answer_text.strip()}
""".strip()

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

def build_final_report_prompt(compact: Dict[str, Any]) -> str:
    return f"""
너는 면접 피드백 리포트를 '정리'하는 편집자다.
규칙:
- 입력에 없는 사실/수치를 절대 만들지 마라.
- 출력은 반드시 JSON만(설명/마크다운 금지).
- 반드시 question.text(면접 질문)를 기준으로 요약/강점/액션플랜을 작성하라.
- strengths/weaknesses는 각 2~4개.
- action_plans_json은 3~7개, title/description만.

반드시 아래 스키마 그대로 출력:
{{
  "summary_headline": "한 줄 요약",
  "overall_feedback": "전체 피드백(문단)",

  "visual_summary": "visual 요약(짧게)",
  "voice_summary": "voice 요약(짧게)",
  "content_summary": "content 요약(짧게)",

  "visual_strengths_json": ["...", "..."],
  "visual_weaknesses_json": ["...", "..."],
  "voice_strengths_json": ["...", "..."],
  "voice_weaknesses_json": ["...", "..."],
  "content_strengths_json": ["...", "..."],
  "content_weaknesses_json": ["...", "..."],

  "action_plans_json": [
    {{"title":"...", "description":"..." }}
  ]
}}

입력:
{safe_json(compact)}
""".strip()
