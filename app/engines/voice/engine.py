from __future__ import annotations

from typing import Any, Dict, List, Optional
import os

import numpy as np
import librosa

from app.engines.common.result import ok_result, error_result


def _safe_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def _count_silence_intervals(
    y: np.ndarray,
    sr: int,
    *,
    top_db: int = 30,
    frame_length: int = 2048,
    hop_length: int = 256,
    min_silence_sec: float = 0.25,
) -> int:
    """
    librosa.effects.split -> non-silent 구간들 반환
    그 complement를 silence로 보고, min_silence_sec 이상인 silence 구간 개수만 센다.
    """
    non_silent = librosa.effects.split(
        y=y,
        top_db=top_db,
        frame_length=frame_length,
        hop_length=hop_length,
    )

    total_samples = len(y)
    silence_count = 0
    cur = 0

    for start, end in non_silent:
        start = int(start)
        end = int(end)

        if start > cur:
            # [cur, start) 가 silence
            dur_sec = (start - cur) / float(sr)
            if dur_sec >= min_silence_sec:
                silence_count += 1

        cur = max(cur, end)

    # tail silence
    if cur < total_samples:
        dur_sec = (total_samples - cur) / float(sr)
        if dur_sec >= min_silence_sec:
            silence_count += 1

    return int(silence_count)


def _compute_avg_pitch_hz(
    y: np.ndarray,
    sr: int,
    *,
    fmin_hz: float = 65.0,
    fmax_hz: float = 2093.0,
    frame_length: int = 2048,
    hop_length: int = 256,
) -> Optional[float]:
    """
    pyin으로 f0 추정 후, 유효한(=nan 아닌) f0의 평균만 반환.
    실패/무성구간만이면 None.
    """
    f0, _, _ = librosa.pyin(
        y=y,
        fmin=fmin_hz,
        fmax=fmax_hz,
        sr=sr,
        frame_length=frame_length,
        hop_length=hop_length,
    )
    if f0 is None or len(f0) == 0:
        return None

    voiced = f0[~np.isnan(f0)]
    if voiced.size == 0:
        return None

    return _safe_float(np.mean(voiced))


def _compute_avg_wpm(stt_text: Optional[str], duration_sec: float) -> Optional[int]:
    """
    DB 스키마가 INT라 MVP에서는 정수로 반환(반올림).
    """
    if not stt_text:
        return None
    if duration_sec <= 0:
        return None

    words = [w for w in stt_text.strip().split() if w]
    if not words:
        return None

    wpm = len(words) / (duration_sec / 60.0)
    return int(round(wpm))


def _compute_max_wpm(stt_segments: Optional[List[Dict[str, Any]]]) -> Optional[int]:
    """
    segment별로 (단어 수 / segment duration) 으로 wpm 계산 후 최대값 반환 (정수 반올림)
    segments: [{"start": float, "end": float, "text": str}, ...]
    """
    if not stt_segments:
        return None

    max_wpm: Optional[float] = None

    for seg in stt_segments:
        try:
            start = float(seg.get("start", 0.0))
            end = float(seg.get("end", 0.0))
            text = (seg.get("text") or "").strip()
            dur = max(0.0, end - start)

            if dur <= 0.0 or not text:
                continue

            words = [w for w in text.split() if w]
            if not words:
                continue

            wpm = len(words) / (dur / 60.0)
            if (max_wpm is None) or (wpm > max_wpm):
                max_wpm = wpm
        except Exception:
            continue

    if max_wpm is None:
        return None
    return int(round(max_wpm))


def run_voice(
    audio_path: str,
    stt_text: Optional[str] = None,
    stt_segments: Optional[List[Dict[str, Any]]] = None,
    *,
    # silence params (MVP 기본값)
    silence_top_db: int = 30,
    min_silence_sec: float = 0.25,
    # pyin params (MVP 기본값)
    fmin_hz: float = 65.0,
    fmax_hz: float = 2093.0,
) -> Dict[str, Any]:
    """
    Voice 엔진 (MVP: raw 측정만)
    - metrics: avg_wpm, max_wpm, silence_count, avg_pitch 만 반환
    - events: 항상 []
    """
    try:
        if not audio_path:
            raise ValueError("audio_path is required")
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"audio file not found: {audio_path}")

        y, sr = librosa.load(audio_path, sr=None, mono=True)
        if y is None or len(y) == 0:
            raise ValueError("audio is empty or could not be loaded")

        duration_sec = float(len(y) / sr)

        avg_pitch = _compute_avg_pitch_hz(
            y, sr,
            fmin_hz=fmin_hz,
            fmax_hz=fmax_hz,
        )

        silence_count = _count_silence_intervals(
            y, sr,
            top_db=silence_top_db,
            min_silence_sec=min_silence_sec,
        )

        avg_wpm = _compute_avg_wpm(stt_text, duration_sec)
        max_wpm = _compute_max_wpm(stt_segments)

        metrics: Dict[str, Any] = {
            "avg_wpm": avg_wpm,               # INT or None
            "max_wpm": max_wpm,               # INT or None
            "silence_count": int(silence_count),
            "avg_pitch": avg_pitch,           # FLOAT or None
        }

        return ok_result("voice", metrics=metrics, events=[])

    except Exception as e:
        return error_result("voice", error_type="VOICE_ERROR", message=str(e))



# from typing import Any, Dict
# from app.engines.common.result import ok_result, error_result

# def run_voice(audio_path: str) -> Dict[str, Any]:
#     """
#     Voice 엔진 stub (v0 규격 반환)
#     - 아직 실제 분석 전: metrics/events 비움
#     """
#     try:
#         if not audio_path:
#             raise ValueError("audio_path is required")

#         # TODO: 실제 voice 분석 지표 추가 예정
#         metrics: Dict[str, Any] = {}
#         events = []
#         return ok_result("voice", metrics=metrics, events=events)

#     except Exception as e:
#         return error_result("voice", error_type="VOICE_ERROR", message=str(e))
