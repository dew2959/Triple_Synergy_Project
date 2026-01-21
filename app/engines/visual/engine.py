from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from app.engines.common.result import ok_result, error_result
from app.engines.visual.timestamp_utils import compute_timestamp_ms



MODULE_NAME = "visual"

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
        fps = float(fps) if fps and fps > 0 else 30.0

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

        # ✅ POS_MSEC가 0부터 시작하지 않거나 들쭉날쭉할 수 있어서 기준점(base) 보정
        base_ts_ms: Optional[float] = None

        forced_inc = 0  # timestamp strict 증가 강제된 횟수

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

            # --------------------------------------------------------
            # ✅ timestamp 생성 (유틸로 분리)
            # --------------------------------------------------------
            raw_pos_msec = cap.get(cv2.CAP_PROP_POS_MSEC)
            pos_frames = cap.get(cv2.CAP_PROP_POS_FRAMES)

            prev_before = prev_ts_ms

            timestamp_ms, base_ts_ms, prev_ts_ms = compute_timestamp_ms(
                raw_pos_msec=raw_pos_msec,
                pos_frames=pos_frames,
                fps=fps,
                base_ts_ms=base_ts_ms,
                prev_ts_ms=prev_before,
                max_ts_ms=10_000_000,
            )

            # strict 증가 강제가 발생했는지 체크
            # (timestamp가 prev+1로 나온 경우는 강제 보정일 가능성이 높음)
            if prev_before >= 0 and timestamp_ms == prev_before + 1:
                forced_inc += 1


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

        print(f"[visual] forced_increase_count={forced_inc} sampled={sampled}")

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
