import os
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.engines.common.result import ok_result, error_result

# ✅ .env 로드: 엔진 단독 실행에서도 OPENAI_API_KEY를 읽게 함
try:
    from dotenv import load_dotenv
    # engine.py 위치: .../app/engines/content/engine.py
    # project root: .../ (app 폴더 상위)
    PROJECT_ROOT = Path(__file__).resolve().parents[3]
    load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=False)
except Exception:
    # python-dotenv 미설치/경로 이슈여도 엔진이 죽지 않게
    pass

MODULE_NAME = "content"

# -----------------------------
# 간단 토크나이저(한국어 토큰 대충 뽑기)
# -----------------------------
def _tokenize_ko(text: str) -> List[str]:
    return re.findall(r"[가-힣]{2,}", text or "")

def _top_keywords(text: str, k: int = 7) -> List[str]:
    toks = _tokenize_ko(text)
    # 너무 흔한 단어(완전 stopword 수준만 간단히 제거)
    stop = {"저는", "제가", "그때", "그리고", "그래서", "때문에", "합니다", "했습니다", "있습니다", "것입니다"}
    toks = [t for t in toks if t not in stop]
    # 빈도 상위 k개
    freq: Dict[str, int] = {}
    for t in toks:
        freq[t] = freq.get(t, 0) + 1
    return [w for w, _ in sorted(freq.items(), key=lambda x: (-x[1], x[0]))[:k]]

def _clamp_int(x: Any, lo: int = 0, hi: int = 100) -> int:
    try:
        v = int(round(float(x)))
    except Exception:
        v = 0
    return max(lo, min(hi, v))

def _calc_wpm(answer_text: str, duration_sec: Optional[float]) -> int:
    """
    한국어는 공백이 '단어' 기준으로 완벽하진 않지만,
    MVP에서 속도 proxy로는 충분.
    """
    if not answer_text:
        return 0
    if not duration_sec or duration_sec <= 0:
        return 0
    words = [w for w in (answer_text or "").split() if w.strip()]
    minutes = duration_sec / 60.0
    return int(round(len(words) / minutes)) if minutes > 0 else 0

# -----------------------------
# OpenAI 호출 (있으면 사용)
# -----------------------------
def _call_llm_json(
    question_text: str,
    answer_text: str,
    model: str,
) -> Dict[str, Any]:
    """
    OpenAI Python SDK(v1) 기준: from openai import OpenAI
    - response_format json_object 사용
    """
    from openai import OpenAI  # 로컬 import (키 없으면 여기서 실패 가능)
    client = OpenAI()

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

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
    )
    content = resp.choices[0].message.content or "{}"
    return json.loads(content)

# -----------------------------
# 키 없을 때/실패할 때 fallback (발표 안정성)
# -----------------------------
def _rule_based_analyze(
    question_text: str,
    answer_text: str,
    duration_sec: Optional[float],
) -> Dict[str, Any]:
    """
    LLM 없이도 최소한의 점수/피드백을 만들어내는 규칙 기반.
    완벽하지 않아도 "흐름이 끊기지 않는 것"이 목적.
    """
    text = (answer_text or "").strip()
    n_chars = len(text)
    kws = _top_keywords(text, k=7)

    # logic_score: 길이 + 구체성(숫자/경험 단서) 기반 아주 단순 proxy
    has_numbers = bool(re.search(r"\d", text))
    has_example = any(w in text for w in ["예를", "경험", "프로젝트", "문제", "해결", "개선", "성과"])
    logic = 40
    logic += 20 if n_chars >= 200 else 0
    logic += 20 if has_example else 0
    logic += 10 if has_numbers else 0
    logic_score = _clamp_int(logic)

    # job_fit_score: 질문 단어 일부가 답변에 얼마나 겹치는지(매우 러프)
    q_toks = set(_tokenize_ko(question_text))
    a_toks = set(_tokenize_ko(text))
    overlap = len(q_toks & a_toks)
    job_fit_score = _clamp_int(45 + overlap * 6)

    # time_management_score: duration이 있으면 너무 짧거나 너무 길면 감점(러프)
    tm = 70
    if duration_sec and duration_sec > 0:
        if duration_sec < 30:
            tm -= 25
        elif duration_sec > 180:
            tm -= 15
    else:
        # duration이 없으면 텍스트 길이로만
        if n_chars < 120:
            tm -= 20
        elif n_chars > 700:
            tm -= 10
    time_management_score = _clamp_int(tm)

    feedback_parts = []
    if n_chars < 150:
        feedback_parts.append("답변이 다소 짧아 핵심 근거(경험/수치)가 부족합니다.")
    if not has_example:
        feedback_parts.append("구체적 사례(상황-행동-결과)를 1개 넣으면 설득력이 올라갑니다.")
    if duration_sec and duration_sec > 180:
        feedback_parts.append("길이가 길어 요점 중심으로 구조화하면 더 좋습니다.")
    if not feedback_parts:
        feedback_parts.append("전체 구조가 비교적 명확합니다. 핵심 성과를 수치로 한 번 더 강조해보세요.")

    feedback = " ".join(feedback_parts[:3])

    model_answer = (
        "핵심 강점 1문장 → 구체 사례(문제/행동/결과) → 직무 연결 1문장 순으로 짧게 정리해보세요."
    )

    return {
        "logic_score": logic_score,
        "job_fit_score": job_fit_score,
        "time_management_score": time_management_score,
        "feedback": feedback,
        "recommended_keywords": kws,
        "model_answer": model_answer,
        "method": "rule_based",
    }

# -----------------------------
# v0 엔진 엔트리
# -----------------------------
def run_content(
    answer_text: str,
    question_text: str = "",
    duration_sec: Optional[float] = None,
    model: str = "gpt-4o-mini",
) -> Dict[str, Any]:
    """
    Content(LLM) 엔진 - v0 반환

    - answer_text 필수
    - OPENAI_API_KEY가 있으면 LLM 호출, 없거나 실패하면 rule-based fallback
    """
    try:
        if answer_text is None or answer_text.strip() == "":
            return error_result(MODULE_NAME, "CONTENT_ERROR", "answer_text is required")

        q = question_text or ""
        a = answer_text or ""

        # 선택: WPM도 metrics로는 제공 가능(저장은 플랫폼에서 결정)
        wpm = _calc_wpm(a, duration_sec)

        use_llm = bool(os.getenv("OPENAI_API_KEY"))
        analysis: Dict[str, Any]

        if use_llm:
            try:
                analysis = _call_llm_json(q, a, model=model)
                analysis["method"] = "openai"
            except Exception:
                # LLM 실패 시에도 끊기지 않게 fallback
                analysis = _rule_based_analyze(q, a, duration_sec)
        else:
            analysis = _rule_based_analyze(q, a, duration_sec)

        logic_score = _clamp_int(analysis.get("logic_score", 0))
        job_fit_score = _clamp_int(analysis.get("job_fit_score", 0))
        time_management_score = _clamp_int(analysis.get("time_management_score", 0))
        feedback = (analysis.get("feedback") or "").strip()
        model_answer = (analysis.get("model_answer") or "").strip()

        keywords = analysis.get("recommended_keywords") or analysis.get("keywords") or []
        if not isinstance(keywords, list):
            keywords = []
        keywords = [str(k).strip() for k in keywords if str(k).strip()]

        metrics: Dict[str, Any] = {
            # ✅ DB(answer_content_analysis)에 바로 매핑 가능한 키들
            "logic_score": logic_score,
            "job_fit_score": job_fit_score,
            "time_management_score": time_management_score,
            "feedback": feedback,
            "model_answer": model_answer,
            "keywords": keywords,

            # ✅ 운영/디버그용 (DB 저장은 선택)
            "wpm": int(wpm),
            "method": analysis.get("method", "unknown"),
            "model": model,
        }

        return ok_result(MODULE_NAME, metrics=metrics, events=[])

    except Exception as e:
        return error_result(MODULE_NAME, type(e).__name__, str(e))










# from typing import Any, Dict
# from app.engines.common.result import ok_result, error_result

# def run_content(text: str) -> Dict[str, Any]:
#     """
#     Content 엔진 stub (v0 규격 반환)
#     - 아직 실제 분석 전: metrics/events 비움
#     """
#     try:
#         if text is None or text == "":
#             raise ValueError("text is required")

#         # TODO: 내용 분석 지표(키워드, 구조 점수 등) metrics로 확장 예정
#         metrics: Dict[str, Any] = {}
#         events = []
#         return ok_result("content", metrics=metrics, events=events)

#     except Exception as e:
#         return error_result("content", error_type="CONTENT_ERROR", message=str(e))
