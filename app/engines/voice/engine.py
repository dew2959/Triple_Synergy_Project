from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import os
import re

import numpy as np
import librosa

from app.engines.common.result import ok_result, error_result


# -------------------------
# small helpers
# -------------------------
def _safe_float(x: Any) -> Optional[float]:
    try:
        return None if x is None else float(x)
    except Exception:
        return None


def _count_chars(text: Optional[str]) -> int:
    """공백 제거 + 한글/영문/숫자만 남기고 길이 카운트."""
    if not text:
        return 0
    s = re.sub(r"\s+", "", text)
    s = re.sub(r"[^0-9A-Za-z가-힣]", "", s)
    return len(s)


# -------------------------
# silence
# -------------------------
def _count_silence_intervals(
    y: np.ndarray,
    sr: int,
    *,
    top_db: int = 30,
    frame_length: int = 2048,
    hop_length: int = 256,
    min_silence_sec: float = 0.25,
) -> int:
    non_silent = librosa.effects.split(
        y=y,
        top_db=top_db,
        frame_length=frame_length,
        hop_length=hop_length,
    )

    total = len(y)
    cur = 0
    cnt = 0

    for start, end in non_silent:
        start, end = int(start), int(end)
        if start > cur:
            dur = (start - cur) / float(sr)
            if dur >= min_silence_sec:
                cnt += 1
        cur = max(cur, end)

    if cur < total:
        dur = (total - cur) / float(sr)
        if dur >= min_silence_sec:
            cnt += 1

    return int(cnt)


# -------------------------
# pitch (pyin)
# -------------------------
def _compute_pitch_stats_hz(
    y: np.ndarray,
    sr: int,
    *,
    fmin_hz: float = 65.0,
    fmax_hz: float = 2093.0,
    frame_length: int = 2048,
    hop_length: int = 512,
) -> Dict[str, Optional[float]]:
    """
    pyin 기반 pitch 통계 (MVP):
    - avg_pitch, max_pitch, pitch_std, voiced_ratio
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
        return {"avg_pitch": None, "max_pitch": None, "pitch_std": None, "voiced_ratio": 0.0}

    voiced = f0[~np.isnan(f0)]
    if voiced.size == 0:
        return {"avg_pitch": None, "max_pitch": None, "pitch_std": None, "voiced_ratio": 0.0}

    avg = _safe_float(np.mean(voiced))
    mx = _safe_float(np.max(voiced))
    std = _safe_float(np.std(voiced))
    voiced_ratio = float(voiced.size / float(len(f0)))

    return {
        "avg_pitch": avg,
        "max_pitch": mx,
        "pitch_std": std,
        "voiced_ratio": voiced_ratio,
    }


# -------------------------
# speed (CPS/CPM)
# -------------------------
def _compute_avg_cps_cpm(
    stt_text: Optional[str],
    duration_sec: float,
) -> Tuple[Optional[float], Optional[float], Optional[int]]:
    if not stt_text or duration_sec <= 0:
        return None, None, None

    char_count = _count_chars(stt_text)
    if char_count <= 0:
        return None, None, 0

    avg_cps = float(char_count / duration_sec)
    avg_cpm = float(avg_cps * 60.0)
    return avg_cps, avg_cpm, int(char_count)


def _compute_instability_from_segments(
    stt_segments: Optional[List[Dict[str, Any]]],
    *,
    min_seg_sec: float = 0.15,
    k_fast: float = 1.30,
) -> Dict[str, Optional[float]]:
    """
    세그먼트 CPS로 불안정 지표만 반환 (MVP):
    - burst_ratio = max_cps / median_cps
    - high_speed_share = proportion(cps > median*k_fast)
    - cv_cps = std / mean
    """
    if not stt_segments:
        return {"burst_ratio": None, "high_speed_share": None, "cv_cps": None}

    cps_list: List[float] = []
    for seg in stt_segments:
        text = seg.get("text") or ""
        start = seg.get("start")
        end = seg.get("end")
        if start is None or end is None:
            continue

        dur = float(end) - float(start)
        if dur <= min_seg_sec:
            continue

        chars = _count_chars(text)
        if chars <= 0:
            continue

        cps_list.append(chars / dur)

    if not cps_list:
        return {"burst_ratio": None, "high_speed_share": None, "cv_cps": None}

    arr = np.array(cps_list, dtype=float)
    med = float(np.percentile(arr, 50))
    mean = float(np.mean(arr))
    std = float(np.std(arr))
    mx = float(np.max(arr))

    burst_ratio = float(mx / med) if med > 0 else None
    high_speed_share = float(np.mean(arr > (med * k_fast))) if med > 0 else None
    cv_cps = float(std / mean) if mean > 0 else None

    return {
        "burst_ratio": burst_ratio,
        "high_speed_share": high_speed_share,
        "cv_cps": cv_cps,
    }


# -------------------------
# legacy (WPM) - keep for service compatibility
# -------------------------
def _compute_avg_wpm(stt_text: Optional[str], duration_sec: float) -> Optional[int]:
    if not stt_text or duration_sec <= 0:
        return None
    words = [w for w in stt_text.strip().split() if w]
    if not words:
        return None
    wpm = len(words) / (duration_sec / 60.0)
    return int(round(wpm))


def _compute_max_wpm(stt_segments: Optional[List[Dict[str, Any]]]) -> Optional[int]:
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

    return None if max_wpm is None else int(round(max_wpm))


# -------------------------
# main
# -------------------------
def run_voice(
    audio_path: str,
    stt_text: Optional[str] = None,
    stt_segments: Optional[List[Dict[str, Any]]] = None,
    *,
    # silence params
    silence_top_db: int = 35,
    min_silence_sec: float = 0.25,
    # pyin params
    fmin_hz: float = 65.0,
    fmax_hz: float = 2093.0,
) -> Dict[str, Any]:
    """
    Voice 엔진 (MVP: raw 측정만)
    - 서비스 호환을 위해 avg_wpm/max_wpm/duration 키는 유지
    - 한국어 속도 평가는 avg_cpm + 불안정(burst/share/cv) 중심
    """
    try:
        if not audio_path:
            raise ValueError("audio_path is required")
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"audio file not found: {audio_path}")

        y, sr = librosa.load(audio_path, sr=16000, mono=True)
        if y is None or len(y) == 0:
            raise ValueError("audio is empty or could not be loaded")

        duration_sec = float(len(y) / sr)

        pitch = _compute_pitch_stats_hz(y, sr, fmin_hz=fmin_hz, fmax_hz=fmax_hz)
        silence_count = _count_silence_intervals(y, sr, top_db=silence_top_db, min_silence_sec=min_silence_sec)
        silence_rate_30s = silence_count / max(duration_sec, 1e-6) * 30.0

        # legacy WPM (호환)
        avg_wpm = _compute_avg_wpm(stt_text, duration_sec)
        max_wpm = _compute_max_wpm(stt_segments)

        # CPS/CPM (한국어 친화)
        avg_cps, avg_cpm, char_count = _compute_avg_cps_cpm(stt_text, duration_sec)

        # 불안정(세그먼트 기반)
        inst = _compute_instability_from_segments(stt_segments)

        metrics: Dict[str, Any] = {
            # compatibility
            "avg_wpm": avg_wpm,
            "max_wpm": max_wpm,
            "silence_count": int(silence_rate_30s),
            "duration_sec": duration_sec,
            # "duration": duration_sec,  # AnalysisService 호환

            # pitch core
            "avg_pitch": pitch["avg_pitch"],
            "max_pitch": pitch["max_pitch"],
            "pitch_std": pitch["pitch_std"],
            "voiced_ratio": pitch["voiced_ratio"],

            # speed core
            "char_count": char_count,
            "avg_cps": avg_cps,
            "avg_cpm": avg_cpm,

            # instability core
            "burst_ratio": inst["burst_ratio"],
            "high_speed_share": inst["high_speed_share"],
            "cv_cps": inst["cv_cps"],
        }

        return ok_result("voice", metrics=metrics, events=[])

    except Exception as e:
        return error_result("voice", error_type="VOICE_ERROR", message=str(e))
