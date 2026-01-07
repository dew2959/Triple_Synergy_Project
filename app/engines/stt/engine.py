import os
import math
from typing import Any, Dict, List, Optional

import whisper  # openai-whisper (pip package)

from app.engines.common.result import ok_result, error_result

MODULE_NAME = "stt"

# Whisper 모델은 로드가 비싸서 프로세스 내 캐시 권장
_MODEL: Optional[Any] = None


def _get_model(model_name: str = "small") -> Any:
    global _MODEL
    if _MODEL is None:
        _MODEL = whisper.load_model(model_name)
    return _MODEL


def _confidence_proxy_from_segments(segments: List[Dict[str, Any]]) -> float:
    """
    코랩에서 쓰던 방식 유지:
    mean(exp(avg_logprob)) over segments
    - Whisper segments에 avg_logprob가 없을 수도 있어 fallback 처리
    """
    if not segments:
        return 0.0
    vals: List[float] = []
    for s in segments:
        lp = s.get("avg_logprob")
        if lp is None:
            # 없으면 매우 낮은 값으로 간주
            lp = -10.0
        try:
            vals.append(math.exp(float(lp)))
        except Exception:
            vals.append(math.exp(-10.0))
    return float(sum(vals) / len(vals)) if vals else 0.0


def run_stt(
    audio_path: str,
    model_name: str = "base",
    language: Optional[str] = None,   # 예: "ko"
) -> Dict[str, Any]:
    """
    STT 엔진 (Whisper) - v0 규격 반환

    반환(metrics)에 최소로 넣을 것(플랫폼 연동 목적):
    - text: 전체 transcript
    - confidence_proxy: segment 기반 proxy score (0~1 근처일 수 있으나 완전한 확률은 아님)
    - segments: timestamp 포함 (필요 시 플랫폼/LLM에서 활용)
    """
    try:
        if not audio_path:
            return error_result(MODULE_NAME, "STT_ERROR", "audio_path is required")

        if not os.path.exists(audio_path):
            return error_result(MODULE_NAME, "STT_ERROR", f"audio file not found: {audio_path}")

        if os.path.getsize(audio_path) <= 0:
            return error_result(MODULE_NAME, "STT_ERROR", f"audio file is empty: {audio_path}")

        model = _get_model(model_name)

        # CPU 환경이면 fp16=False가 안전
        # language를 주면(예: ko) 더 안정적일 때가 있음
        transcribe_kwargs: Dict[str, Any] = {"fp16": False}
        if language:
            transcribe_kwargs["language"] = language

        stt_result = model.transcribe(audio_path, **transcribe_kwargs)

        full_text = (stt_result.get("text") or "").strip()
        segments = stt_result.get("segments") or []

        # segments 정리(너무 큰 필드가 있으면 최소 필드만 남기는 게 좋음)
        slim_segments: List[Dict[str, Any]] = []
        for s in segments:
            slim_segments.append(
                {
                    "id": s.get("id"),
                    "start": float(s.get("start", 0.0)),
                    "end": float(s.get("end", 0.0)),
                    "text": (s.get("text") or "").strip(),
                    "avg_logprob": s.get("avg_logprob"),
                    "no_speech_prob": s.get("no_speech_prob"),
                }
            )

        confidence_proxy = _confidence_proxy_from_segments(segments)

        metrics: Dict[str, Any] = {
            "text": full_text,
            "confidence_proxy": float(confidence_proxy),
            "segments": slim_segments,   # 플랫폼/LLM에서 타임라인 필요하면 바로 사용 가능 (현재는 DB에 저장하지 않음)
            "model_name": model_name,
            "language": language,
        }

        return ok_result(MODULE_NAME, metrics=metrics, events=[])

    except Exception as e:
        # 예외를 밖으로 터뜨리지 않고 v0 error로 반환
        return error_result(MODULE_NAME, type(e).__name__, str(e))


















# from typing import Any, Dict
# from app.engines.common.result import ok_result, error_result

# def run_stt(audio_path: str) -> Dict[str, Any]:
#     """
#     STT 엔진 stub (v0 규격 반환)
#     - 아직 실제 STT 전: metrics/events 비움
#     """
#     try:
#         if not audio_path:
#             raise ValueError("audio_path is required")

#         # TODO: STT 결과 텍스트/신뢰도 등을 metrics(또는 artifacts)로 확장 예정
#         metrics: Dict[str, Any] = {}
#         events = []
#         return ok_result("stt", metrics=metrics, events=events)

#     except Exception as e:
#         return error_result("stt", error_type="STT_ERROR", message=str(e))
