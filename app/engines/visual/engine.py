from __future__ import annotations  # (타입 힌트에서 아직 정의되지 않은 클래스를 문자열 없이 쓰게 해줌. 파이썬 3.7+에서 유용)

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2                   # 영상 프레임 읽기
import numpy as np            # std(표준편차) 등 통계 계산
import mediapipe as mp        # MediaPipe Image 래퍼
from mediapipe.tasks import python
from mediapipe.tasks.python import vision  # FaceLandmarker 등 vision task

from app.engines.common.result import ok_result, error_result  # 공통 리턴 포맷 생성 헬퍼


MODULE_NAME = "visual"  # 결과에 들어갈 모듈 이름(엔진 이름)

# ------------------------------------------------------------
# (1) 모델/분석 파라미터
# ------------------------------------------------------------

DEFAULT_MODEL_PATH = str(
    (Path(__file__).resolve().parent / "models" / "face_landmarker.task")
)

TARGET_FPS = 10
NOSE_CENTER_RANGE: Tuple[float, float] = (0.40, 0.60)
NOSE_LANDMARK_IDX = 0
STD_REF = 0.02
MAX_SAMPLES = 600

_LANDMARKER: Optional[vision.FaceLandmarker] = None


def _clamp01(x: float) -> float:
    return float(max(0.0, min(1.0, x)))


def build_face_landmarker(model_path: str) -> vision.FaceLandmarker:
    base_options = python.BaseOptions(model_asset_path=model_path)

    options = vision.FaceLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO,
        num_faces=1,
        output_face_blendshapes=False,
        output_facial_transformation_matrixes=False,
    )

    return vision.FaceLandmarker.create_from_options(options)


def _get_landmarker() -> vision.FaceLandmarker:
    global _LANDMARKER
    if _LANDMARKER is None:
        _LANDMARKER = build_face_landmarker(DEFAULT_MODEL_PATH)
    return _LANDMARKER


def run_visual(video_path: str) -> Dict[str, Any]:
    try:
        if not video_path or not isinstance(video_path, str):
            return error_result(MODULE_NAME, "InvalidInput", "video_path is required (non-empty string).")

        if not os.path.exists(video_path):
            return error_result(MODULE_NAME, "FileNotFound", f"video_path does not exist: {video_path}")

        if not os.path.exists(DEFAULT_MODEL_PATH):
            return error_result(
                MODULE_NAME,
                "ModelNotFound",
                f"FaceLandmarker model (.task) not found: {DEFAULT_MODEL_PATH}",
            )

        landmarker = _get_landmarker()

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return error_result(MODULE_NAME, "VideoOpenFailed", f"Failed to open video: {video_path}")

        # ------------------------------------------------------------
        # (3) 샘플링 설정
        # ------------------------------------------------------------
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        fps = float(fps) if fps > 0 else 30.0

        step = max(1, int(round(fps / max(1, TARGET_FPS))))

        # ------------------------------------------------------------
        # (4) 프레임별로 쌓을 값들
        # ------------------------------------------------------------
        face_present: List[bool] = []
        nose_x: List[Optional[float]] = []

        frame_idx = 0
        sampled = 0

        # ✅ MediaPipe는 timestamp가 "항상 증가"해야 함
        prev_ts_ms = -1

        # ------------------------------------------------------------
        # (5) 비디오 프레임 루프
        # ------------------------------------------------------------
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # 샘플링: step에 안 맞으면 skip
            if frame_idx % step != 0:
                frame_idx += 1
                continue

            sampled += 1
            if sampled > MAX_SAMPLES:
                break

            # ✅ timestamp_ms 생성: trunc(int) 대신 round로 중복 위험 줄이기
            #    그리고 혹시라도 같은 값이 나오면 prev+1로 강제 증가(단조 증가 보장)
            raw_ts_ms = int(round((frame_idx / fps) * 1000.0))
            timestamp_ms = raw_ts_ms if raw_ts_ms > prev_ts_ms else (prev_ts_ms + 1)
            prev_ts_ms = timestamp_ms

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

            # FaceLandmarker 실행
            result = landmarker.detect_for_video(mp_image, timestamp_ms)

            if result.face_landmarks:
                face_present.append(True)
                nose = result.face_landmarks[0][NOSE_LANDMARK_IDX]
                nose_x.append(float(nose.x))
            else:
                face_present.append(False)
                nose_x.append(None)

            frame_idx += 1

        cap.release()

        if not face_present:
            return error_result(MODULE_NAME, "NoFrames", "No frames were processed from the video.")

        # ------------------------------------------------------------
        # (7) metric 계산
        # ------------------------------------------------------------
        face_presence_ratio = _clamp01(sum(face_present) / len(face_present))

        lo, hi = NOSE_CENTER_RANGE
        valid_x = [v for v in nose_x if v is not None]

        head_center_ratio = _clamp01(
            (sum(1 for v in valid_x if lo <= v <= hi) / len(valid_x)) if valid_x else 0.0
        )

        diffs: List[float] = []
        prev: Optional[float] = None

        for v in nose_x:
            if v is None:
                prev = None
                continue
            if prev is not None:
                diffs.append(abs(v - prev))
            prev = v

        std_raw = float(np.std(diffs)) if diffs else 0.0
        head_movement_std = _clamp01(std_raw / STD_REF)

        metrics = {
            "face_presence_ratio": float(face_presence_ratio),
            "head_center_ratio": float(head_center_ratio),
            "head_movement_std": float(head_movement_std),
        }

        return ok_result(MODULE_NAME, metrics=metrics, events=[])

    except Exception as e:
        return error_result(MODULE_NAME, type(e).__name__, str(e))
