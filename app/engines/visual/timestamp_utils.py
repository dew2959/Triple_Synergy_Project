# app/engines/visual/timestamp_utils.py
from __future__ import annotations

import math
from typing import Optional, Tuple


def _is_finite_number(x) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(float(x))


def compute_timestamp_ms(
    *,
    raw_pos_msec,
    pos_frames,
    fps: float,
    base_ts_ms: Optional[float],
    prev_ts_ms: int,
    max_ts_ms: int = 10_000_000,
) -> Tuple[int, Optional[float], int]:
    """
    MediaPipe detect_for_video용 timestamp(ms) 생성.
    우선순위:
      1) POS_MSEC (base 보정)
      2) fallback: POS_FRAMES/fps 기반
      3) ultimate fallback: prev+1 (최소한 strict increasing 보장)

    Returns:
      (timestamp_ms, base_ts_ms, prev_ts_ms)
    """
    # fps 방어 (너희 코드에서 fps는 기본 30.0이라 보통 안전하지만, 유틸은 방어적으로)
    try:
        fps_f = float(fps)
    except Exception:
        fps_f = 0.0
    if fps_f <= 0:
        raise ValueError(f"fps must be > 0. got {fps}")

    raw_ts_ms: Optional[int] = None

    # 1) POS_MSEC 기반
    if _is_finite_number(raw_pos_msec):
        pos_msec_f = float(raw_pos_msec)

        # 첫 유효 프레임에서 base 세팅
        if base_ts_ms is None:
            base_ts_ms = pos_msec_f

        # base 보정
        raw_ts_ms = int(round(pos_msec_f - float(base_ts_ms)))

        # POS_MSEC가 가끔 음수/이상치가 될 수 있으니 가드
        if raw_ts_ms < 0 or raw_ts_ms > max_ts_ms:
            raw_ts_ms = None

    # 2) fallback: POS_FRAMES 기반
    if raw_ts_ms is None:
        if _is_finite_number(pos_frames):
            pf = float(pos_frames)
            if pf < 0:
                pf = 0.0
            raw_ts_ms = int(round((pf / fps_f) * 1000.0))
        else:
            raw_ts_ms = 0 if prev_ts_ms < 0 else (prev_ts_ms + 1)

    # 3) 최소 0 보정
    if raw_ts_ms < 0:
        raw_ts_ms = 0

    # 4) strict increasing 보장
    timestamp_ms = raw_ts_ms if raw_ts_ms > prev_ts_ms else (prev_ts_ms + 1)
    prev_ts_ms = timestamp_ms

    return timestamp_ms, base_ts_ms, prev_ts_ms
