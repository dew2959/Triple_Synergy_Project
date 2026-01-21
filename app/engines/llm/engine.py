from __future__ import annotations

import os
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.engines.common.result import ok_result, error_result
from app.utils.prompt_utils import sanitize_text, filter_or_raise, build_content_messages
from app.core.config import Settings

# ============================================================
# ✅ .env 로드
# - 엔진을 단독 실행할 때도 OPENAI_API_KEY를 읽도록 함
# - dotenv가 없거나 경로 문제가 생겨도 엔진이 죽지 않게 try/except 처리
# ============================================================
try:
    from dotenv import load_dotenv

    # engine.py 위치: .../app/engines/content/engine.py
    # project root: .../ (app 폴더 상위)
    PROJECT_ROOT = Path(__file__).resolve().parents[3]
    load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=False)
except Exception:
    # python-dotenv 미설치/경로 이슈여도 엔진이 죽지 않게 pass
    pass

MODULE_NAME = "content"


# ============================================================
# 1) 간단 토크나이저(한국어 토큰 대충 뽑기)
# - LLM이 없을 때(rule-based fallback) 키워드/유사도용으로 사용
# ============================================================
def _tokenize_ko(text: str) -> List[str]:
    """한글 2글자 이상 토큰만 추출(아주 단순)"""
    return re.findall(r"[가-힣]{2,}", text or "")


def _top_keywords(text: str, k: int = 7) -> List[str]:
    """
    빈도 기반 상위 키워드 k개 뽑기 (아주 러프)
    - 흔한 말투/불용어(stopwords) 일부 제거
    """
    toks = _tokenize_ko(text)
    stop = {"저는", "제가", "그때", "그리고", "그래서", "때문에", "합니다", "했습니다", "있습니다", "것입니다"}
    toks = [t for t in toks if t not in stop]

    # 빈도 집계
    freq: Dict[str, int] = {}
    for t in toks:
        freq[t] = freq.get(t, 0) + 1

    # 빈도 내림차순 + 알파벳(가나다) 오름차순 정렬 후 k개
    return [w for w, _ in sorted(freq.items(), key=lambda x: (-x[1], x[0]))[:k]]


def _clamp_int(x: Any, lo: int = 0, hi: int = 100) -> int:
    """
    점수 값 안전 변환:
    - 숫자로 변환 실패하면 0
    - 범위는 lo~hi로 clamp
    """
    try:
        v = int(round(float(x)))
    except Exception:
        v = 0
    return max(lo, min(hi, v))


# ============================================================
# 2) OpenAI 호출 (키가 있으면 사용)
# - response_format={"type":"json_object"}로 JSON 강제
# - 실패하면 상위에서 rule-based로 fallback
# ============================================================
def _call_llm_json(question_text: str, answer_text: str, model: str) -> Dict[str, Any]:
    from openai import OpenAI
    client = OpenAI(api_key=Settings.OPENAI_API_KEY)

    q = sanitize_text(question_text)
    a = sanitize_text(answer_text)

    filter_or_raise(q, where="content.question")
    filter_or_raise(a, where="content.answer")

    messages = build_content_messages(q, a)

    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        response_format={"type": "json_object"},
    )

    content = resp.choices[0].message.content or "{}"
    return json.loads(content)

# ============================================================
# 3) 키 없을 때/실패할 때 fallback (발표 안정성)
# - LLM 호출이 실패해도 "흐름이 끊기지 않게" 최소 결과 생성
# ============================================================
def _rule_based_analyze(
    question_text: str,
    answer_text: str,
    duration_sec: Optional[float],
) -> Dict[str, Any]:
    """
    LLM 없이도 최소 점수/피드백을 만들어내는 규칙 기반 분석.
    목적: "완벽"이 아니라 "끊기지 않음(안정성)".
    """
    text = (answer_text or "").strip()
    n_chars = len(text)

    # 간단 키워드 추출
    kws = _top_keywords(text, k=7)

    # --------------------------
    # logic_score: 길이 + 구체성 힌트 기반(아주 단순 proxy)
    # --------------------------
    has_numbers = bool(re.search(r"\d", text))  # 숫자 포함 여부
    has_example = any(w in text for w in ["예를", "경험", "프로젝트", "문제", "해결", "개선", "성과"])

    logic = 40
    logic += 20 if n_chars >= 200 else 0
    logic += 20 if has_example else 0
    logic += 10 if has_numbers else 0
    logic_score = _clamp_int(logic)

    # --------------------------
    # job_fit_score: 질문-답변 토큰 겹침 정도(아주 러프)
    # --------------------------
    q_toks = set(_tokenize_ko(question_text))
    a_toks = set(_tokenize_ko(text))
    overlap = len(q_toks & a_toks)
    job_fit_score = _clamp_int(45 + overlap * 6)

    # --------------------------
    # time_management_score: 길이/전개 적절성 proxy
    # - duration이 있으면 너무 짧거나 길면 감점
    # - duration이 없으면 텍스트 길이로만 감점
    # --------------------------
    tm = 70
    if duration_sec and duration_sec > 0:
        if duration_sec < 30:
            tm -= 25
        elif duration_sec > 180:
            tm -= 15
    else:
        if n_chars < 120:
            tm -= 20
        elif n_chars > 700:
            tm -= 10
    time_management_score = _clamp_int(tm)

    # --------------------------
    # feedback: 조건에 맞게 최대 3문장 구성
    # --------------------------
    feedback_parts: List[str] = []
    if n_chars < 150:
        feedback_parts.append("답변이 다소 짧아 핵심 근거(경험/수치)가 부족합니다.")
    if not has_example:
        feedback_parts.append("구체적 사례(상황-행동-결과)를 1개 넣으면 설득력이 올라갑니다.")
    if duration_sec and duration_sec > 180:
        feedback_parts.append("길이가 길어 요점 중심으로 구조화하면 더 좋습니다.")
    if not feedback_parts:
        feedback_parts.append("전체 구조가 비교적 명확합니다. 핵심 성과를 수치로 한 번 더 강조해보세요.")

    feedback = " ".join(feedback_parts[:3])

    # model_answer: 아주 짧은 템플릿 형태
    model_answer = "핵심 강점 1문장 → 구체 사례(문제/행동/결과) → 직무 연결 1문장 순으로 짧게 정리해보세요."

    return {
        "logic_score": logic_score,
        "job_fit_score": job_fit_score,
        "time_management_score": time_management_score,
        "feedback": feedback,
        "recommended_keywords": kws,
        "model_answer": model_answer,
        # 디버그: 어떤 방식으로 분석했는지 표기
        "method": "rule_based",
    }


# ============================================================
# 4) v0 엔진 엔트리
# - v0 contract 준수: 항상 metrics(dict), events(list), error(null or dict)
# - answer_text 필수
# - OPENAI_API_KEY 있으면 LLM 시도, 실패하면 rule-based fallback
# - ✅ 요청사항: wpm 관련 로직/필드 모두 제거
# ============================================================
def run_content(
    answer_text: str,
    question_text: str = "",
    duration_sec: Optional[float] = None,
    model: str = "gpt-4o-mini",
) -> Dict[str, Any]:
    """
    Content(LLM) 엔진 - v0 반환

    - answer_text: 필수
    - question_text: 선택(있으면 분석 품질 올라감)
    - duration_sec: 선택(시간/전개 평가 proxy에 활용)
    - OPENAI_API_KEY가 있으면 LLM 호출, 없거나 실패하면 rule-based fallback
    """
    try:
        # 1) 필수 입력 검증 (없으면 v0 error_result)
        if answer_text is None or answer_text.strip() == "":
            return error_result(MODULE_NAME, "CONTENT_ERROR", "answer_text is required")

        # 2) 입력 정리(빈 문자열 방어)
        q = question_text or ""
        a = answer_text or ""

        # 3) LLM 사용 가능 여부 판단
        use_llm = bool(os.getenv("OPENAI_API_KEY"))
        analysis: Dict[str, Any]

        # 4) LLM 시도 → 실패 시 fallback
        if use_llm:
            try:
                analysis = _call_llm_json(q, a, model=model)
                analysis["method"] = "openai"  # 디버그용
            except Exception:
                analysis = _rule_based_analyze(q, a, duration_sec)
        else:
            analysis = _rule_based_analyze(q, a, duration_sec)

        # 5) 안전한 값 꺼내기(점수 clamp, 문자열 strip)
        logic_score = _clamp_int(analysis.get("logic_score", 0))
        job_fit_score = _clamp_int(analysis.get("job_fit_score", 0))
        time_management_score = _clamp_int(analysis.get("time_management_score", 0))

        feedback = (analysis.get("feedback") or "").strip()
        model_answer = (analysis.get("model_answer") or "").strip()

        # keywords 키 호환: recommended_keywords 또는 keywords 허용
        keywords = analysis.get("recommended_keywords") or analysis.get("keywords") or []
        if not isinstance(keywords, list):
            keywords = []
        keywords = [str(k).strip() for k in keywords if str(k).strip()]

        # 6) metrics 구성
        # - DB(answer_content_analysis) 매핑 가능한 키는 고정
        # - method/model은 테스트/운영 디버그용으로 남김(요청 반영)
        metrics: Dict[str, Any] = {
            # ✅ DB(answer_content_analysis)에 바로 매핑 가능한 키들
            "logic_score": logic_score,
            "job_fit_score": job_fit_score,
            "time_management_score": time_management_score,
            "feedback": feedback,
            "model_answer": model_answer,
            "keywords": keywords,  # DB에는 keywords_json(JSONB)에 저장

            # ✅ 운영/디버그용 (DB 저장은 선택)
            "method": analysis.get("method", "unknown"),
            "model": model,
        }

        # 7) v0 contract: events는 MVP에서는 항상 []
        return ok_result(MODULE_NAME, metrics=metrics, events=[])

    except Exception as e:
        # 엔진은 예외를 터뜨리지 않고 error_result로 감싸서 반환
        return error_result(MODULE_NAME, type(e).__name__, str(e))
