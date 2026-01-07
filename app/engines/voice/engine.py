from __future__ import annotations

from typing import Any, Dict, List, Optional
import os

import numpy as np
import librosa

from app.engines.common.result import ok_result, error_result


def _safe_float(x: Any) -> Optional[float]:
    """어떤 값이든 float로 안전하게 변환. 실패하면 None."""
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
    ✅ 침묵(silence) 구간 개수 계산 (MVP: count만)

    아이디어:
    - librosa.effects.split()은 'non-silent(소리가 있는) 구간들'을 [start, end] 샘플 인덱스로 반환함
    - 그 "보이는(non-silent) 구간들의 여집합(complement)"을 silence로 간주
    - silence 구간 중 min_silence_sec 이상인 구간만 '침묵'으로 카운트

    파라미터:
    - top_db: 이 값이 작을수록 더 엄격(조금만 작아도 소리로 판단), 클수록 더 관대
    - frame_length/hop_length: split이 분석하는 프레임 단위(정밀도/속도에 영향)
    - min_silence_sec: 너무 짧은 침묵(예: 0.05s)은 무시하기 위한 필터
    """
    non_silent = librosa.effects.split(
        y=y,
        top_db=top_db,
        frame_length=frame_length,
        hop_length=hop_length,
    )

    total_samples = len(y)
    silence_count = 0
    cur = 0  # 현재 커서(이전 non-silent 끝지점)

    # non-silent 구간들 사이의 '빈 구간'을 silence로 계산
    for start, end in non_silent:
        start = int(start)
        end = int(end)

        if start > cur:
            # [cur, start) 구간이 silence
            dur_sec = (start - cur) / float(sr)
            if dur_sec >= min_silence_sec:
                silence_count += 1

        # 커서를 non-silent의 끝으로 갱신
        cur = max(cur, end)

    # 마지막 non-silent 이후 tail 구간도 silence일 수 있음
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
    hop_length: int = 512,
) -> Optional[float]:
    """
    ✅ 평균 pitch(Hz) 계산 (MVP: 평균만)

    - librosa.pyin()으로 f0(기본 주파수) 추정
    - f0 결과에는 무성구간이 NaN으로 들어올 수 있음
    - 유효한(=NaN이 아닌) f0 값만 평균을 내서 반환
    - 전부 NaN이면(None/무성) None 반환

    파라미터:
    - fmin_hz/fmax_hz: pitch 탐색 범위
      (너무 좁으면 추정 실패/왜곡, 너무 넓으면 잡음에 흔들릴 수 있음)
    - frame_length/hop_length: 시간 해상도/속도에 영향
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

    # 무성 구간은 NaN → 제외
    voiced = f0[~np.isnan(f0)]
    if voiced.size == 0:
        return None

    return _safe_float(np.mean(voiced))


def _compute_avg_wpm(stt_text: Optional[str], duration_sec: float) -> Optional[int]:
    """
    ✅ 평균 WPM 계산 (MVP: 정수 반올림)

    - STT text 전체 기준
    - duration_sec(전체 길이)가 필요
    - DB 스키마가 INT라서 MVP에선 int로 반환(반올림)

    주의:
    - 한국어는 공백 기반 '단어'가 완벽한 지표는 아님(그래도 proxy로 OK)
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
    ✅ 최대 WPM 계산 (MVP: segment 단위 속도 중 최대값)

    - segments: [{"start": float, "end": float, "text": str}, ...]
    - 각 segment마다:
      wpm = (단어 수 / segment duration(분))
    - 그 중 최대값을 반환 (정수 반올림)

    주의:
    - segment duration이 아주 짧으면 wpm이 비정상적으로 커질 수 있음(노이즈)
      (MVP에서는 일단 그대로 두고, 나중에 min_dur filter 추가 고려 가능)
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

            # duration이 0이거나 text가 비어있으면 skip
            if dur <= 0.0 or not text:
                continue

            words = [w for w in text.split() if w]
            if not words:
                continue

            wpm = len(words) / (dur / 60.0)
            if (max_wpm is None) or (wpm > max_wpm):
                max_wpm = wpm
        except Exception:
            # segment 구조가 깨졌거나 타입이 이상하면 해당 segment만 skip
            continue

    if max_wpm is None:
        return None
    return int(round(max_wpm))


def run_voice(
    audio_path: str,
    stt_text: Optional[str] = None,
    stt_segments: Optional[List[Dict[str, Any]]] = None,
    *,
    # ✅ silence params (MVP 기본값)
    silence_top_db: int = 30,
    min_silence_sec: float = 0.25,
    # ✅ pyin params (MVP 기본값)
    fmin_hz: float = 65.0,
    fmax_hz: float = 2093.0,
) -> Dict[str, Any]:
    """
    Voice 엔진 (MVP: raw 측정만)

    ✅ 목표:
    - "측정만" 한다 (해석/스코어링/피드백은 서비스/LLM에서 담당)
    - DB(answer_voice_analysis)로 바로 매핑 가능한 raw metrics만 생성

    반환:
    - metrics: avg_wpm, max_wpm, silence_count, avg_pitch
    - events: MVP에서는 항상 [] (나중에 silence timeline 필요하면 확장 가능)
    """
    try:
        # ----------------------------------------------------
        # 1) 입력 검증
        # ----------------------------------------------------
        if not audio_path:
            raise ValueError("audio_path is required")
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"audio file not found: {audio_path}")

        # ----------------------------------------------------
        # 2) 오디오 로드
        # - sr=None: 원본 샘플레이트 유지 -> (시간 감소를 위해 다운 샘플링) 16000 변경
        # - mono=True: 채널 섞어서 모노로 변환(분석 단순화)
        # ----------------------------------------------------
        y, sr = librosa.load(audio_path, sr=16000, mono=True)
        if y is None or len(y) == 0:
            raise ValueError("audio is empty or could not be loaded")

        # 전체 길이(초) 계산: 샘플 수 / 샘플레이트
        duration_sec = float(len(y) / sr)

        # ----------------------------------------------------
        # 3) pitch 측정 (평균 f0)
        # - 무성구간만 있거나 실패하면 None
        # ----------------------------------------------------
        avg_pitch = _compute_avg_pitch_hz(
            y, sr,
            fmin_hz=fmin_hz,
            fmax_hz=fmax_hz,
        )

        # ----------------------------------------------------
        # 4) 침묵 구간 개수 측정
        # - non-silent의 complement를 silence로 처리
        # ----------------------------------------------------
        silence_count = _count_silence_intervals(
            y, sr,
            top_db=silence_top_db,
            min_silence_sec=min_silence_sec,
        )

        # ----------------------------------------------------
        # 5) WPM 계산 (STT가 주어질 때만)
        # - avg_wpm: 전체 stt_text 기반
        # - max_wpm: segment별 기반
        # ----------------------------------------------------
        avg_wpm = _compute_avg_wpm(stt_text, duration_sec)
        max_wpm = _compute_max_wpm(stt_segments)

        # ----------------------------------------------------
        # 6) metrics 구성 (DB 매핑 우선)
        # ----------------------------------------------------
        metrics: Dict[str, Any] = {
            "avg_wpm": avg_wpm,               # INT or None
            "max_wpm": max_wpm,               # INT or None
            "silence_count": int(silence_count),
            "avg_pitch": avg_pitch,           # FLOAT or None
        }

        # ----------------------------------------------------
        # 7) v0 contract 준수: events는 MVP에서 []
        # ----------------------------------------------------
        return ok_result("voice", metrics=metrics, events=[])

    except Exception as e:
        # 예외를 바깥으로 던지지 않고 v0 error로 반환
        return error_result("voice", error_type="VOICE_ERROR", message=str(e))
