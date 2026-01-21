import os
import math
from typing import Any, Dict, List, Optional

import whisper  # openai-whisper (pip package)

from app.engines.common.result import ok_result, error_result

MODULE_NAME = "stt"

# ============================================================
# ✅ Whisper 모델 로드는 비용이 큼
# - 매 호출마다 load_model 하면 매우 느려짐
# - 프로세스 내에서 1번만 로드하고 재사용하기 위해 전역 캐시 사용
# ============================================================
_MODEL: Optional[Any] = None


def _get_model(model_name: str = "small") -> Any:
    """
    Whisper 모델을 1번만 로드해서 재사용하는 헬퍼 함수
    - _MODEL이 None이면 처음 한 번 로드
    - 이미 로드되어 있으면 그대로 반환
    """
    global _MODEL
    if _MODEL is None:
        _MODEL = whisper.load_model(model_name)
    return _MODEL


def _confidence_proxy_from_segments(segments: List[Dict[str, Any]]) -> float:
    """
    ✅ Whisper 결과의 segments를 기반으로 confidence proxy 계산

    - 코랩에서 쓰던 방식 유지:
      mean(exp(avg_logprob)) over segments

    - avg_logprob는 segment별 평균 로그확률(음수 값이 흔함)
    - exp(avg_logprob)를 취하면 (0~1 사이에 가까운 값)처럼 보일 수 있으나
      "진짜 확률"은 아니고, 비교용 proxy 스코어로 쓰는 용도

    - Whisper 세그먼트에 avg_logprob가 없을 수도 있어서:
      없으면 매우 낮은 값(-10)으로 fallback 처리
    """
    if not segments:
        return 0.0

    vals: List[float] = []
    for s in segments:
        lp = s.get("avg_logprob")
        if lp is None:
            # avg_logprob가 없으면 "신뢰도가 매우 낮다"고 가정
            lp = -10.0
        try:
            vals.append(math.exp(float(lp)))
        except Exception:
            # 혹시 lp가 이상한 타입이면 동일하게 낮은 값 처리
            vals.append(math.exp(-10.0))

    # 평균값 반환 (segments가 비어있으면 0.0)
    return float(sum(vals) / len(vals)) if vals else 0.0


def run_stt(
    audio_path: str,
    model_name: str = "small",
    language: Optional[str] = "ko",   # 예: "ko"
) -> Dict[str, Any]:
    """
    STT 엔진 (Whisper) - v0 규격 반환

    ✅ 반환(metrics)에 포함하는 핵심 값:
    - text: 전체 transcript 텍스트
    - confidence_proxy: segment 기반 proxy score (비교용)
    - segments: 타임스탬프 포함 segment 리스트
      (플랫폼/LLM에서 타임라인 활용 가능, MVP에서는 DB 저장 안 해도 됨)
    - model_name: 사용한 whisper 모델
    - language: 지정 언어(예: ko). None이면 whisper가 자동 감지할 수도 있음

    ✅ v0 contract 준수:
    - 성공: ok_result("stt", metrics=..., events=[])
    - 실패: error_result("stt", ..., ...)  (예외 터뜨리지 않음)
    """
    try:
        # ----------------------------------------------------
        # 1) 입력 검증: audio_path 유효성 및 파일 존재/크기 체크
        # ----------------------------------------------------
        if not audio_path:
            return error_result(MODULE_NAME, "STT_ERROR", "audio_path is required")

        if not os.path.exists(audio_path):
            return error_result(MODULE_NAME, "STT_ERROR", f"audio file not found: {audio_path}")

        if os.path.getsize(audio_path) <= 0:
            return error_result(MODULE_NAME, "STT_ERROR", f"audio file is empty: {audio_path}")

        # ----------------------------------------------------
        # 2) Whisper 모델 로드 (전역 캐시)
        # ----------------------------------------------------
        model = _get_model(model_name)

        # ----------------------------------------------------
        # 3) transcribe 옵션 설정
        # - CPU 환경이면 fp16=False가 안전 (fp16은 GPU에서 주로 사용)
        # - language를 주면(예: "ko") 언어 추정이 흔들릴 때 안정적일 수 있음
        # ----------------------------------------------------
        transcribe_kwargs: Dict[str, Any] = {"fp16": False}
        if language:
            transcribe_kwargs["language"] = language

        # ----------------------------------------------------
        # 4) STT 수행
        # - stt_result는 dict 형태로 text/segments 등을 포함
        # ----------------------------------------------------
        stt_result = model.transcribe(audio_path, **transcribe_kwargs)

        # 전체 텍스트 추출
        full_text = (stt_result.get("text") or "").strip()

        # 세그먼트 리스트 추출 (없으면 빈 리스트)
        segments = stt_result.get("segments") or []

        # ----------------------------------------------------
        # 5) segments를 "슬림 버전"으로 정리
        # - Whisper segments에는 다양한 키가 들어있고 용량이 커질 수 있음
        # - MVP/플랫폼 연동 목적에 필요한 필드만 남김
        # ----------------------------------------------------
        slim_segments: List[Dict[str, Any]] = []
        for s in segments:
            slim_segments.append(
                {
                    "id": s.get("id"),
                    "start": float(s.get("start", 0.0)),
                    "end": float(s.get("end", 0.0)),
                    "text": (s.get("text") or "").strip(),
                    # confidence proxy 계산에 활용 가능
                    "avg_logprob": s.get("avg_logprob"),
                    # 무음으로 판단될 확률(Whisper가 주는 힌트)
                    "no_speech_prob": s.get("no_speech_prob"),
                }
            )

        # ----------------------------------------------------
        # 6) confidence proxy 계산
        # - segments의 avg_logprob 기반
        # ----------------------------------------------------
        confidence_proxy = _confidence_proxy_from_segments(segments)

        # ----------------------------------------------------
        # 7) v0 metrics 구성
        # ----------------------------------------------------
        metrics: Dict[str, Any] = {
            "text": full_text,
            "confidence_proxy": float(confidence_proxy),
            "segments": slim_segments,   # 타임라인 기반 후처리(예: wpm/침묵) 가능
            "model_name": model_name,
            "language": language,
        }

        # ----------------------------------------------------
        # 8) v0 contract 성공 반환
        # - events는 MVP에서는 빈 리스트
        # ----------------------------------------------------
        return ok_result(MODULE_NAME, metrics=metrics, events=[])

    except Exception as e:
        # ----------------------------------------------------
        # 9) 예외를 밖으로 터뜨리지 않고 v0 error로 반환
        # ----------------------------------------------------
        return error_result(MODULE_NAME, type(e).__name__, str(e))
