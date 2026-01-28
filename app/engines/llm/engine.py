from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# LangChain
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# Common & Utils
from app.engines.common.result import ok_result, error_result
from app.utils.prompt_utils import sanitize_text
from app.core.config import settings

from app.schemas.content import ContentAnalysisOut

# .env 로드 (단독 실행 시 필요)
try:
    from dotenv import load_dotenv
    PROJECT_ROOT = Path(__file__).resolve().parents[3]
    load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=False)
except Exception:
    pass

MODULE_NAME = "content"



# -------------------------------------------------------------------------
# 2. Rule-Based Fallback (LLM 실패 시 사용)
# -------------------------------------------------------------------------
def _tokenize_ko(text: str) -> List[str]:
    return re.findall(r"[가-힣]{2,}", text or "")

def _top_keywords(text: str, k: int = 7) -> List[str]:
    toks = _tokenize_ko(text)
    stop = {"저는", "제가", "그때", "그리고", "그래서", "때문에", "합니다", "했습니다", "있습니다", "것입니다"}
    toks = [t for t in toks if t not in stop]
    freq: Dict[str, int] = {}
    for t in toks: freq[t] = freq.get(t, 0) + 1
    return [w for w, _ in sorted(freq.items(), key=lambda x: (-x[1], x[0]))[:k]]

def _clamp_int(x: Any, lo: int = 0, hi: int = 100) -> int:
    try:
        v = int(round(float(x)))
    except Exception:
        v = 0
    return max(lo, min(hi, v))

def _rule_based_analyze(question_text: str, answer_text: str, duration_sec: Optional[float]) -> Dict[str, Any]:
    text = (answer_text or "").strip()
    n_chars = len(text)
    kws = _top_keywords(text, k=7)

    has_numbers = bool(re.search(r"\d", text))
    has_example = any(w in text for w in ["예를", "경험", "프로젝트", "문제", "해결", "개선", "성과"])

    logic = 40 + (20 if n_chars >= 200 else 0) + (20 if has_example else 0) + (10 if has_numbers else 0)
    
    q_toks = set(_tokenize_ko(question_text))
    a_toks = set(_tokenize_ko(text))
    overlap = len(q_toks & a_toks)
    job_fit = 45 + overlap * 6

    tm = 70
    if duration_sec and duration_sec > 0:
        if duration_sec < 30: tm -= 25
        elif duration_sec > 180: tm -= 15
    else:
        if n_chars < 120: tm -= 20
        elif n_chars > 700: tm -= 10

    feedback_parts = []
    if n_chars < 150: feedback_parts.append("답변이 짧아 핵심 근거가 부족합니다.")
    if not has_example: feedback_parts.append("구체적 사례를 포함하면 설득력이 높아집니다.")
    if not feedback_parts: feedback_parts.append("구조가 명확합니다. 핵심 성과를 수치로 강조해보세요.")
    
    return {
        "logic_score": _clamp_int(logic),
        "job_fit_score": _clamp_int(job_fit),
        "time_management_score": _clamp_int(tm),
        "feedback": " ".join(feedback_parts[:3]),
        "recommended_keywords": kws,
        "model_answer": "핵심 강점 → 구체 사례 → 직무 연결 순으로 정리해보세요.",
        "method": "rule_based"
    }

# -------------------------------------------------------------------------
# 3. Main Engine Function (LangChain)
# -------------------------------------------------------------------------
def run_content(
    answer_text: str,
    question_text: str = "",
    duration_sec: Optional[float] = None,
    model: str = "gpt-4o",  # 기본값 변경 (필요시 gpt-4o-mini 등 사용)
) -> Dict[str, Any]:
    """
    Content(LLM) 엔진 - LangChain 적용 버전
    """
    try:
        # 1) 필수 검증
        if not answer_text or not answer_text.strip():
            return error_result(MODULE_NAME, "CONTENT_ERROR", "answer_text is required")

        # 2) 입력 정리
        q = sanitize_text(question_text or "")
        a = sanitize_text(answer_text or "")
        
        # 3) LLM 사용 여부
        api_key = settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
        
        metrics = {}
        used_method = "rule_based"

        # 4) LangChain 실행
        if api_key:
            try:
                llm = ChatOpenAI(
                    model=model,
                    api_key=api_key,
                    temperature=0.3
                )
                
                prompt = ChatPromptTemplate.from_messages([
                    ("system", """
                    너는 10년 차 시니어 면접관이다.
                    지원자의 답변을 분석하여 논리성, 직무적합성, 시간관리를 평가하라.

                    [평가 기준]
                    - logic_score (0~100):
                    * 90~100: 도입-전개-결론이 명확, 근거/사례 구체적, 논리적 연결 자연스러움
                    * 70~89: 구조는 있으나 일부 비약/중복, 근거가 다소 약함
                    * 40~69: 흐름이 산만, 핵심 논지 불명확, 사례/근거 부족
                    * 0~39: 질문과 무관하거나 주장만 있고 근거/구조 없음

                    - job_fit_score (0~100):
                    * 90~100: 질문 의도 정확히 파악, 직무 핵심역량(예: 기획/제작/협업/데이터 등)과 직접 연결, 회사/직무 맥락 반영
                    * 70~89: 직무 연관성은 있으나 연결이 약하거나 직무 언어가 부족
                    * 40~69: 일반론 위주, 직무와 연결이 간접적
                    * 0~39: 직무와 거의 무관, 자기PR만 반복

                    - time_management_score (0~100):
                    * 90~100: 핵심만 간결, 불필요한 서론/중복 없음, 전개 속도 적절
                    * 70~89: 대체로 적절하나 다소 장황/짧음, 일부 중복
                    * 40~69: 너무 길거나 너무 짧아 메시지 전달 실패, 핵심보다 배경 설명 과다
                    * 0~39: 질문 답변이 성립되지 않을 정도로 시간/전개 관리 실패

                    [출력 규칙]
                    - 점수는 반드시 0~100 정수
                    - feedback은 3문장 이내, '무엇을/왜/어떻게'가 포함되게
                    - model_answer는 3~5문장 요약 형태
                    - recommended_keywords는 5~10개, 쉼표로 구분
                    """),
                    ("human", """
                    [면접 질문]
                    {question}

                    [지원자 답변]
                    {answer}
                    
                    위 내용을 분석해줘.
                    """)
                ])
                
                # Structured Output (JSON 파싱 자동화)
                chain = prompt | llm.with_structured_output(ContentAnalysisOut)
                
                result: ContentAnalysisOut = chain.invoke({"question": q, "answer": a})
                
                metrics = result.model_dump()
                used_method = "openai_langchain"
                
            except Exception as e:
                print(f"⚠️ [LangChain Engine Error] Fallback to rule-based: {e}")
                metrics = _rule_based_analyze(q, a, duration_sec)
        else:
            metrics = _rule_based_analyze(q, a, duration_sec)

        # 5) 최종 반환 데이터 구성
        # 키워드 필드명 통일 (keywords <- recommended_keywords)
        keywords = metrics.get("recommended_keywords", [])
        
        final_metrics = {
            "logic_score": _clamp_int(metrics.get("logic_score", 0)),
            "job_fit_score": _clamp_int(metrics.get("job_fit_score", 0)),
            "time_management_score": _clamp_int(metrics.get("time_management_score", 0)),
            "feedback": metrics.get("feedback", "").strip(),
            "model_answer": metrics.get("model_answer", "").strip(),
            "keywords": keywords,  # DB 호환용 이름
            
            # 메타데이터
            "method": used_method,
            "model": model,
        }

        return ok_result(MODULE_NAME, metrics=final_metrics, events=[])

    except Exception as e:
        return error_result(MODULE_NAME, type(e).__name__, str(e))