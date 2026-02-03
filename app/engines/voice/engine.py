from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import os

import re
import numpy as np
import librosa

from app.engines.common.result import ok_result, error_result


def _safe_float(x: Any) -> Optional[float]:
    """
    ✅ 어떤 값이든 float로 안전하게 변환하는 헬퍼

    왜 필요?
    - numpy scalar(np.float32), Decimal, str("3.14") 등 타입이 섞여 들어올 수 있음
    - 이걸 그대로 JSON/DB로 넘기면 타입 호환 이슈가 생길 수 있어서 float로 통일하려는 의도
    - 변환이 불가능한 값(None, "", "N/A", dict 등)은 None을 반환해서 "측정 실패/없음" 표현

    반환:
    - 성공: float
    - 실패: None
    """
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

    핵심 아이디어:
    - librosa.effects.split()은 "침묵이 아닌 구간(non-silent)"을 찾아서
      [start_sample, end_sample] 형태로 여러 구간을 반환한다.
    - 우리는 그 non-silent 구간들의 "사이"와 "앞/뒤 남는 부분"을 침묵으로 간주한다(= complement).
    - 그 침묵이 너무 짧으면(예: 0.05초) 의미 없을 수 있으니 min_silence_sec 이상만 카운트한다.

    파라미터:
    - top_db:
        * 작으면: 조금만 작아도 소리로 인정 → 침묵이 덜 잡힘(더 엄격)
        * 크면: 조용한 소리도 침묵으로 봄 → 침묵이 더 잡힘(더 관대)
    - frame_length/hop_length:
        * "프레임 기반 분석"의 창 크기/이동 간격
        * hop이 작을수록 짧은 침묵도 잘 잡지만 계산량이 증가
    - min_silence_sec:
        * 이보다 짧은 침묵 구간은 무시 (노이즈/숨 같은 짧은 공백 필터)
    """

    # 1) 소리 있는 구간(non-silent)만 찾는다.
    # 반환 예시: array([[  5000, 20000], [26000, 40000]])
    # 의미: 5000~20000샘플, 26000~40000샘플 구간에 소리가 있다.
    non_silent = librosa.effects.split(
        y=y,
        top_db=top_db,
        frame_length=frame_length,
        hop_length=hop_length,
    )

    # 2) 전체 길이를 샘플 단위로 확보
    total_samples = len(y)

    # 3) 침묵 구간 개수 누적 변수
    silence_count = 0

    # 4) 커서(cur)는 "지금까지 처리한 끝 지점" (초기=0, 오디오 시작)
    cur = 0

    # 5) non-silent 구간들 사이의 빈 구간을 침묵으로 센다.
    for start, end in non_silent:
        # librosa가 numpy int로 줄 수 있어서 파이썬 int로 통일
        start = int(start)
        end = int(end)

        # start가 cur보다 크면 [cur, start) 사이가 "소리 없는 구간" = 침묵 후보
        if start > cur:
            # 샘플 차이를 초로 바꾸는 공식: (샘플수 / sr) = 초
            dur_sec = (start - cur) / float(sr)

            # 너무 짧은 침묵은 노이즈일 수 있으니 필터
            if dur_sec >= min_silence_sec:
                silence_count += 1

        # 커서를 이번 non-silent 구간의 끝으로 옮김
        # max를 쓰는 이유: 혹시 구간이 겹치거나 비정상일 때 커서가 뒤로 가지 않게 안전 처리
        cur = max(cur, end)

    # 6) 마지막 non-silent 이후 tail(끝부분)도 침묵일 수 있음
    # 예: 마지막 소리 이후로 파일 끝까지 조용하면 그것도 침묵 구간 1개로 카운트
    if cur < total_samples:
        dur_sec = (total_samples - cur) / float(sr)
        if dur_sec >= min_silence_sec:
            silence_count += 1

    # 항상 int 반환
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

    무엇을 계산?
    - pitch = 기본 주파수(f0, fundamental frequency)
    - librosa.pyin()은 프레임마다 f0를 추정해서 배열로 반환한다.
    - 무성 구간(말소리 없는 구간)은 f0가 NaN으로 나오는 것이 정상이다.
    - 그래서 NaN이 아닌 값만 뽑아서 평균낸다.
    - 전부 NaN(= 거의 무성/추정 실패)이면 None 반환.

    파라미터:
    - fmin_hz/fmax_hz:
        * 피치 탐색 범위. 너무 좁으면 추정 실패, 너무 넓으면 노이즈에 흔들릴 수 있음
    - frame_length/hop_length:
        * 프레임 기반 추정의 시간 해상도/안정성 트레이드오프
    """

    # pyin 반환: (f0, voiced_flag, voiced_prob)
    # f0는 Hz 또는 NaN들로 구성된 1D 배열
    f0, _, _ = librosa.pyin(
        y=y,
        fmin=fmin_hz,
        fmax=fmax_hz,
        sr=sr,
        frame_length=frame_length,
        hop_length=hop_length,
    )

    # pyin이 실패하면 f0가 None이거나 빈 배열일 수 있음
    if f0 is None or len(f0) == 0:
        return None

    # 무성 구간은 NaN → 제외하고 "유효한 f0"만 모음
    voiced = f0[~np.isnan(f0)]
    if voiced.size == 0:
        return None

    # 평균 f0를 float로 안전 변환해서 반환
    return _safe_float(np.mean(voiced))

### pitch 추가 함수 ###

def _compute_pitch_stats_hz(y, sr, fmin_hz: float, fmax_hz: float) -> Dict[str, Optional[float]]:
    """
    pyin 기반 pitch 통계(std/range/max). 무성구간은 NaN이라 제거 후 통계.
    """
    import librosa
    f0, voiced_flag, voiced_probs = librosa.pyin(
        y,
        fmin=fmin_hz,
        fmax=fmax_hz,
        sr=sr,
    )
    if f0 is None or len(f0) == 0:
        return {"avg_pitch": None, "max_pitch": None, "pitch_std": None, "pitch_range": None, "voiced_ratio": 0.0}

    voiced = f0[~np.isnan(f0)]
    if len(voiced) == 0:
        return {"avg_pitch": None, "max_pitch": None, "pitch_std": None, "pitch_range": None, "voiced_ratio": 0.0}

    avg = float(np.mean(voiced))
    mx = float(np.max(voiced))
    std = float(np.std(voiced))

    p95 = float(np.percentile(voiced, 95))
    p5  = float(np.percentile(voiced, 5))
    prange = float(p95 - p5)

    voiced_ratio = float(len(voiced) / len(f0))
    return {"avg_pitch": avg, "max_pitch": mx, "pitch_std": std, "pitch_range": prange, "voiced_ratio": voiced_ratio}


### CPS 추가 내용 ####

def _count_chars(text: Optional[str]) -> int:
    """한국어/영어 섞여도 안정적으로: 공백 제거 + 기본적인 기호 제거."""
    if not text:
        return 0
    s = re.sub(r"\s+", "", text)
    # 한글/영문/숫자만 남기고 나머지 제거 (기호/이모지 등)
    s = re.sub(r"[^0-9A-Za-z가-힣]", "", s)
    return len(s)

def _compute_avg_cps_cpm(stt_text: Optional[str], duration_sec: float) -> Tuple[Optional[float], Optional[float], Optional[int]]:
    """전체 텍스트 기준 평균 CPS/CPM + char_count"""
    if not stt_text or duration_sec <= 0:
        return None, None, None
    char_count = _count_chars(stt_text)
    if char_count <= 0:
        return None, None, 0
    avg_cps = char_count / duration_sec
    avg_cpm = avg_cps * 60.0
    return float(avg_cps), float(avg_cpm), int(char_count)

def _compute_segment_cps_stats(stt_segments: Optional[List[Dict[str, Any]]]) -> Dict[str, Optional[float]]:
    """
    세그먼트 단위 속도 변동 측정용.
    max 대신 p95를 추천. (노이즈에 덜 민감)
    segments 원소는 {"text":..., "start":..., "end":...} 형태를 기대.
    """
    if not stt_segments:
        return {"p95_cps": None, "max_cps": None}

    cps_list: List[float] = []
    for seg in stt_segments:
        text = seg.get("text") or ""
        start = seg.get("start")
        end = seg.get("end")

        # start/end가 없거나 이상하면 스킵
        if start is None or end is None:
            continue
        dur = float(end) - float(start)
        if dur <= 0.15:  # 너무 짧은 조각은 노이즈라 제외(학생 프로젝트용 안전장치)
            continue

        chars = _count_chars(text)
        if chars <= 0:
            continue

        cps_list.append(chars / dur)

    if not cps_list:
        return {"p95_cps": None, "max_cps": None}

    arr = np.array(cps_list, dtype=float)
    p95 = float(np.percentile(arr, 95))
    mx = float(np.max(arr))
    return {"p95_cps": p95, "max_cps": mx}

def _compute_avg_wpm(stt_text: Optional[str], duration_sec: float) -> Optional[int]:
    """
    ✅ 평균 WPM(분당 단어 수) 계산 (MVP: 정수 반올림)

    입력:
    - stt_text: 전체 STT 결과 문자열
    - duration_sec: 전체 오디오 길이(초)

    계산:
    - words = stt_text를 공백으로 split한 단어 수
    - WPM = 단어 수 / (길이(초)/60)

    반환:
    - DB 스키마가 INT라서 MVP에선 int(round(wpm))로 반환
    - stt_text 없거나 duration_sec <= 0이면 None

    주의:
    - 한국어는 공백 기반 단어가 완벽하지 않지만, 속도 proxy로 사용 가능
    """

    # STT text가 없으면 WPM은 계산 불가
    if not stt_text:
        return None

    # 길이가 0이거나 음수면 나눗셈/의미상 계산 불가
    if duration_sec <= 0:
        return None

    # 문자열 앞뒤 공백 제거 후, 공백 단위 split
    words = [w for w in stt_text.strip().split() if w]
    if not words:
        return None

    # 분당 단어수: 단어수 / (초/60)
    wpm = len(words) / (duration_sec / 60.0)

    # MVP: int로 반올림해서 반환
    return int(round(wpm))


def _compute_max_wpm(stt_segments: Optional[List[Dict[str, Any]]]) -> Optional[int]:
    """
    ✅ 최대 WPM 계산 (MVP: segment 단위 속도 중 최대값)

    입력 segments 형태:
    - [{"start": float, "end": float, "text": str}, ...]

    각 segment마다:
    - dur = end - start (초)
    - words = text.split() 단어 수
    - wpm = words / (dur/60)

    그 중 최대값을 반환 (정수 반올림)

    주의:
    - segment dur이 매우 짧으면 wpm이 튀어버릴 수 있음(예: 0.2초에 단어 1개면 300 WPM)
      → MVP에선 그대로 두고, 나중에 min_dur 필터 추가 고려 가능
    """

    if not stt_segments:
        return None

    max_wpm: Optional[float] = None

    for seg in stt_segments:
        try:
            # seg의 start/end는 타입이 문자열일 수도 있어 float로 통일
            start = float(seg.get("start", 0.0))
            end = float(seg.get("end", 0.0))

            # seg text가 None일 수 있으니 ""로 대체 후 strip
            text = (seg.get("text") or "").strip()

            # dur이 음수일 가능성 방지(데이터 깨짐 대비)
            dur = max(0.0, end - start)

            # dur이 0이거나 text가 비어있으면 이 segment는 스킵
            if dur <= 0.0 or not text:
                continue

            # segment 단어 수
            words = [w for w in text.split() if w]
            if not words:
                continue

            # segment WPM 계산
            wpm = len(words) / (dur / 60.0)

            # 최대값 갱신
            if (max_wpm is None) or (wpm > max_wpm):
                max_wpm = wpm

        except Exception:
            # segment 구조가 이상하거나 타입 변환 실패하면 그 segment만 스킵하고 계속 진행
            continue

    if max_wpm is None:
        return None

    # MVP: 정수 반올림
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

    ✅ 목표(이 설계의 의도):
    - "해석/스코어링/피드백"은 여기서 하지 않는다.
    - 여기서는 오로지 "원시 측정값(raw metrics)"만 만든다.
    - 피드백 문장/좋은점/나쁜점 같은 건 상위 서비스/LLM에서 담당하기 쉬움.

    입력:
    - audio_path: 분석할 오디오 파일 경로
    - stt_text: 전체 STT 텍스트(없으면 WPM 계산 불가)
    - stt_segments: segment 단위 STT 결과(없으면 max_wpm 계산 불가)

    출력(v0 contract):
    - ok_result("voice", metrics=..., events=[])
    - metrics: avg_wpm, max_wpm, silence_count, avg_pitch
    - events: MVP에서는 항상 [] (나중에 침묵 타임라인 등 이벤트로 확장 가능)
    """

    try:
        # ----------------------------------------------------
        # 1) 입력 검증(가장 흔한 실패 원인: 경로 없음/파일 없음)
        # ----------------------------------------------------
        if not audio_path:
            raise ValueError("audio_path is required")

        # 파일이 실제로 있는지 체크 (경로 오타/업로드 실패 대응)
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"audio file not found: {audio_path}")

        # ----------------------------------------------------
        # 2) 오디오 로드
        # - sr=16000: 샘플레이트를 16k로 "통일" (STT/음성처리에서 흔한 표준)
        #             -> 모델/지표 비교를 동일 조건으로 만들기 쉬움
        # - mono=True: 스테레오일 경우 채널을 섞어서 모노로 변환 (분석 단순화)
        #
        # 반환:
        # - y: 1D numpy array (모노 파형)
        # - sr: 실제 사용 샘플레이트(여기서는 16000이 될 가능성이 큼)
        # ----------------------------------------------------
        y, sr = librosa.load(audio_path, sr=16000, mono=True)

        # 로드 실패/빈 오디오 방어
        if y is None or len(y) == 0:
            raise ValueError("audio is empty or could not be loaded")

        # 전체 길이(초) 계산: (샘플 수 / 샘플레이트)
        duration_sec = float(len(y) / sr)

        # ----------------------------------------------------
        # 3) pitch 측정 (평균 f0)
        # - 결과:
        #   * 말소리가 충분하면 avg_pitch는 float(Hz)
        #   * 무성/추정실패면 None
        # ----------------------------------------------------
        pitch_stats = _compute_pitch_stats_hz(
            y, sr, 
            fmin_hz=fmin_hz, 
            fmax_hz=fmax_hz
        )

        # ----------------------------------------------------
        # 4) 침묵 구간 개수 측정
        # - librosa.split이 준 non-silent의 complement를 silence로 계산
        # - silence_count는 항상 int
        # ----------------------------------------------------
        silence_count = _count_silence_intervals(
            y, sr,
            top_db=silence_top_db,
            min_silence_sec=min_silence_sec,
        )

        # ----------------------------------------------------
        # 5) WPM 계산 (STT가 주어질 때만 의미 있음)
        # - avg_wpm: 전체 stt_text 기반
        # - max_wpm: segment별 기반
        # 주의:
        # - stt_text 없으면 avg_wpm=None
        # - stt_segments 없으면 max_wpm=None
        # ----------------------------------------------------
        avg_wpm = _compute_avg_wpm(stt_text, duration_sec)
        max_wpm = _compute_max_wpm(stt_segments)


        # ✅ CPM/CPS 추가
        avg_cps, avg_cpm, char_count = _compute_avg_cps_cpm(stt_text, duration_sec)


        # ✅ segment 기반 p95/max cps + pace_ratio
        seg_stats = _compute_segment_cps_stats(stt_segments)
        p95_cps = seg_stats["p95_cps"]
        max_cps = seg_stats["max_cps"]
        pace_ratio = None
        if avg_cps and p95_cps:
            pace_ratio = float(p95_cps / avg_cps)

        # ----------------------------------------------------
        # 6) metrics 구성 (DB 매핑 우선)
        #
        # 여기서 "타입이 일관된지"가 중요:
        # - avg_wpm, max_wpm: int or None
        # - silence_count: int
        # - avg_pitch: float or None
        # ----------------------------------------------------
        metrics: Dict[str, Any] = {
            # 기존
            "avg_wpm": avg_wpm,
            "max_wpm": max_wpm,
            "silence_count": int(silence_count),

            # pitch (기존 avg_pitch 유지 + 확장)
            "avg_pitch": pitch_stats.get("avg_pitch"),
            "max_pitch": pitch_stats.get("max_pitch"),
            "pitch_std": pitch_stats.get("pitch_std"),
            "pitch_range": pitch_stats.get("pitch_range"),
            "voiced_ratio": pitch_stats.get("voiced_ratio"),

            # ✅ 새 속도 raw metrics
            "duration_sec": duration_sec,
            "char_count": char_count,
            "avg_cps": avg_cps,
            "avg_cpm": avg_cpm,

            # ✅ 변동성/급발진 감지용
            "p95_cps": p95_cps,
            "max_cps": max_cps,
            "pace_ratio": pace_ratio,
        }

        # ----------------------------------------------------
        # 7) v0 contract 준수
        # - events: MVP에선 타임라인 이벤트를 만들지 않으니 []
        # - ok_result가 공통 포맷(meta 포함 등)을 맞춰줄 가능성이 큼
        # ----------------------------------------------------
        return ok_result("voice", metrics=metrics, events=[])

    except Exception as e:
        # ----------------------------------------------------
        # 예외를 밖으로 던지지 않고, v0 error 포맷으로 감싸서 반환
        # - API 서버 입장에선 항상 "정해진 형태"로 응답해서 다루기 쉬워짐
        # ----------------------------------------------------
        return error_result("voice", error_type="VOICE_ERROR", message=str(e))
