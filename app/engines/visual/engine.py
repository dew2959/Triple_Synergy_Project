# import cv2
# import numpy as np
# import mediapipe as mp
# from mediapipe.tasks import python
# from mediapipe.tasks.python import vision
# from typing import Any, Dict, List, Optional, Tuple

# from app.engines.common.result import ok_result, error_result



# def build_face_landmarker(model_path: str) -> vision.FaceLandmarker:
#     base_options = python.BaseOptions(model_asset_path=model_path)
#     options = vision.FaceLandmarkerOptions(
#         base_options=base_options,
#         running_mode=vision.RunningMode.VIDEO,
#         num_faces=1,
#         output_face_blendshapes=False,
#         output_facial_transformation_matrixes=False,
#     )
#     return vision.FaceLandmarker.create_from_options(options)

# def run_visual(
#     video_path: str,
#     model_path: str,
#     landmarker: Optional[vision.FaceLandmarker] = None,
#     target_fps: int = 10,
#     nose_center_range: Tuple[float, float] = (0.40, 0.60),
#     nose_landmark_idx: int = 0,
# ) -> Dict[str, Any]:
#     try:
#         if not video_path:
#             return error_result("visual", "VISUAL_ERROR", "video_path is required")

#         if landmarker is None:
#             landmarker = build_face_landmarker(model_path)

#         cap = cv2.VideoCapture(video_path)
#         if not cap.isOpened():
#             return error_result("visual", "VISUAL_ERROR", f"Failed to open video: {video_path}")

#         fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
#         fps = float(fps) if fps > 0 else 30.0
#         step = max(1, int(round(fps / max(1, target_fps))))

#         face_present: List[bool] = []
#         nose_x: List[Optional[float]] = []

#         frame_idx = 0
#         while True:
#             ret, frame = cap.read()
#             if not ret:
#                 break

#             if frame_idx % step != 0:
#                 frame_idx += 1
#                 continue

#             t_sec = frame_idx / fps
#             timestamp_ms = int(t_sec * 1000)

#             rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
#             mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

#             result = landmarker.detect_for_video(mp_image, timestamp_ms)

#             if result.face_landmarks:
#                 face_present.append(True)
#                 nose = result.face_landmarks[0][nose_landmark_idx]
#                 nose_x.append(float(nose.x))
#             else:
#                 face_present.append(False)
#                 nose_x.append(None)

#             frame_idx += 1

#         cap.release()

#         # ---- metrics 계산 ----
#         face_presence_ratio = (sum(face_present) / len(face_present)) if face_present else 0.0

#         lo, hi = nose_center_range
#         valid_x = [v for v in nose_x if v is not None]

#         head_center_ratio = (
#             sum(1 for v in valid_x if lo <= v <= hi) / len(valid_x)
#             if valid_x else 0.0
#         )

#         # head_movement_std: 연속 프레임 간 이동량(Δx)의 표준편차를 0~1로 정규화
#         diffs = [abs(valid_x[i] - valid_x[i - 1]) for i in range(1, len(valid_x))]
#         std_raw = float(np.std(diffs)) if diffs else 0.0

#         # 정규화 기준(임시): 0.02 이상이면 1.0으로 클램프 (나중에 데이터 보고 조정)
#         std_ref = 0.02
#         head_movement_std = max(0.0, min(std_raw / std_ref, 1.0))

#         metrics = {
#             "face_presence_ratio": float(face_presence_ratio),
#             "head_center_ratio": float(head_center_ratio),
#             "head_movement_std": float(head_movement_std),
#         }

#         # 합의대로 MVP는 events 빈 리스트로
#         return ok_result("visual", metrics=metrics, events=[])

#     except Exception as e:
#         return error_result("visual", "VISUAL_ERROR", str(e))







from typing import Any, Dict, List, Optional
from app.engines.common.result import ok_result, error_result

def run_visual(
    video_path: str,
    # 필요하면 model_path, target_fps 등 추가
) -> Dict[str, Any]:
    """
    Visual 엔진은 v0 계약에 맞춰 dict를 반환한다.
    오늘 목표: metrics 3개(face_presence_ratio, head_center_ratio, head_movement_std)만 반환.
    events는 일단 []로 둔다(추후 확장).
    """
    try:
        if not video_path:
            raise ValueError("video_path is required")

        # TODO: 여기에서 네 mediapipe facemesh 코드로 실제 계산
        # 아래 값들은 지금은 더미 / 또는 계산 결과로 교체
        face_presence_ratio = 1.0
        head_center_ratio = 0.5
        head_movement_std = 0.6

        metrics = {
            "face_presence_ratio": float(face_presence_ratio),
            "head_center_ratio": float(head_center_ratio),
            "head_movement_std": float(head_movement_std),
        }
        return ok_result("visual", metrics=metrics, events=[])

    except Exception as e:
        return error_result("visual", error_type="VISUAL_ERROR", message=str(e))
