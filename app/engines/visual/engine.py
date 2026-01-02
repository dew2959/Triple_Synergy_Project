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


MODULE_NAME = "visual"

# 모델 파일 위치 고정 (플랫폼 최소 변경 목적)
DEFAULT_MODEL_PATH = str(
    (Path(__file__).resolve().parent / "models" / "face_landmarker.task")
)

# 샘플링 목표 FPS (속도/안정성)
TARGET_FPS = 10

# 코 중심 판단 구간 (코가 중앙이라고 볼 x 범위)
NOSE_CENTER_RANGE: Tuple[float, float] = (0.40, 0.60)

# 코 landmark index
NOSE_LANDMARK_IDX = 0

# head_movement_std 정규화 기준(임시): 0.02 이상이면 1.0으로 포화
STD_REF = 0.02

# 너무 긴 영상 방지 (선택): 샘플 수 제한
MAX_SAMPLES = 600  # 10fps면 대략 60초

# FaceLandmarker 재사용 캐시
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
    """
    v0 Raw Output Contract:
    {
      "module": "visual",
      "metrics": {} or {face_presence_ratio, head_center_ratio, head_movement_std},
      "events": [],
      "error": null or {"type": "...", "message": "..."}
    }
    """
    try:
        # ---- 입력 검증 ---- (video_path, 파일 존재 여부, 모델 파일 존재 여부, cv2 open 체크)
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

        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        fps = float(fps) if fps > 0 else 30.0

        step = max(1, int(round(fps / max(1, TARGET_FPS))))

        # 얼굴이 잡혔는지 -> bool
        # 코의 위치 값 -> float
        face_present: List[bool] = []
        nose_x: List[Optional[float]] = []

        frame_idx = 0
        sampled = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # 샘플링
            if frame_idx % step != 0:
                frame_idx += 1
                continue

            sampled += 1
            if sampled > MAX_SAMPLES:
                break

            timestamp_ms = int((frame_idx / fps) * 1000)

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

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

        # ---- metrics 계산 ----
        # face_presence_ratio 낮음 -> 얼굴 검출 불안정 (프레임/조명/각도/가림)
        # head_center_ratio 낮음 -> 화면이 중앙을 벗어난 시간이 많음 (시선/포지션/앵글)
        # head_movement_score 높음 -> 고개 흔들림/움직임이 불규칙 (긴장/제스처/카메라 흔들림)
        face_presence_ratio = _clamp01(sum(face_present) / len(face_present))

        lo, hi = NOSE_CENTER_RANGE
        valid_x = [v for v in nose_x if v is not None]

        head_center_ratio = _clamp01(
            (sum(1 for v in valid_x if lo <= v <= hi) / len(valid_x)) if valid_x else 0.0
        )

        # ✅ head_movement_std: "연속 샘플"에서 둘 다 값 있을 때만 Δx 계산 (결측으로 압축되는 왜곡 방지)
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




# from typing import Any, Dict, List, Optional
# from app.engines.common.result import ok_result, error_result

# def run_visual(
#     video_path: str,
#     # 필요하면 model_path, target_fps 등 추가
# ) -> Dict[str, Any]:
#     """
#     Visual 엔진은 v0 계약에 맞춰 dict를 반환한다.
#     오늘 목표: metrics 3개(face_presence_ratio, head_center_ratio, head_movement_std)만 반환.
#     events는 일단 []로 둔다(추후 확장).
#     """
#     try:
#         if not video_path:
#             raise ValueError("video_path is required")

#         # TODO: 여기에서 네 mediapipe facemesh 코드로 실제 계산
#         # 아래 값들은 지금은 더미 / 또는 계산 결과로 교체
#         face_presence_ratio = 1.0
#         head_center_ratio = 0.5
#         head_movement_std = 0.6

#         metrics = {
#             "face_presence_ratio": float(face_presence_ratio),
#             "head_center_ratio": float(head_center_ratio),
#             "head_movement_std": float(head_movement_std),
#         }
#         return ok_result("visual", metrics=metrics, events=[])

#     except Exception as e:
#         return error_result("visual", error_type="VISUAL_ERROR", message=str(e))
