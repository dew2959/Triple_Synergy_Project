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

# 모델 파일 위치를 "현재 파일 기준"으로 고정
# - 플랫폼/배포 환경에서 상대경로로 안정적으로 찾기 위함
DEFAULT_MODEL_PATH = str(
    (Path(__file__).resolve().parent / "models" / "face_landmarker.task")
)

# 영상 전체를 다 분석하면 느리니까, "몇 FPS로 샘플링할지" 목표
# 예: 영상이 30fps면 10fps로 줄여서 3프레임 중 1프레임만 분석
TARGET_FPS = 10

# "코가 중앙이다"라고 판단할 x 범위(정규화 좌표 0~1 기준)
# x가 0.40~0.60이면 화면 가로 중앙 20% 영역 안에 있다는 뜻
NOSE_CENTER_RANGE: Tuple[float, float] = (0.40, 0.60)

# (중요) 코 landmark index (임시)
# - 지금 코드는 "NOSE_LANDMARK_IDX=0이면 0번 랜드마크를 코라고 가정"하는 상태
# - 실제로 0번이 코라는 보장은 없음(랜드마크 맵으로 확정 필요)
NOSE_LANDMARK_IDX = 0

# head_movement_std를 0~1로 정규화할 때 쓰는 기준값(임시)
# - std_raw / STD_REF => 대략 STD_REF일 때 1.0 근처가 됨
# - 데이터에 따라 조정 필요
STD_REF = 0.02

# 너무 긴 영상에서 계산량 폭증 방지(샘플 수 제한)
# - TARGET_FPS=10이면 600샘플 ≈ 60초 정도만 처리
MAX_SAMPLES = 600

# FaceLandmarker 객체를 전역으로 캐시해서 재사용 (매번 모델 로드 비용 절감)
_LANDMARKER: Optional[vision.FaceLandmarker] = None


def _clamp01(x: float) -> float:
    """
    어떤 값이든 0~1 범위로 잘라주는 함수
    - metric을 항상 0~1로 맞추려고 사용
    """
    return float(max(0.0, min(1.0, x)))


def build_face_landmarker(model_path: str) -> vision.FaceLandmarker:
    """
    FaceLandmarker를 생성하는 팩토리 함수
    - model_asset_path로 .task 모델을 로드
    - VIDEO 모드로 사용(프레임 + timestamp_ms 제공)
    - num_faces=1: 얼굴 1개만 찾음(가장 큰/가장 확실한 얼굴 1개)
    """
    base_options = python.BaseOptions(model_asset_path=model_path)

    options = vision.FaceLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO,   # 비디오 모드: detect_for_video를 사용하며 timestamp 필요
        num_faces=1,                              # 얼굴 최대 1개
        output_face_blendshapes=False,            # 블렌드쉐이프(표정) 필요 없으니 끔
        output_facial_transformation_matrixes=False,  # 3D 변환행렬도 필요 없으니 끔(속도/단순화)
    )

    return vision.FaceLandmarker.create_from_options(options)


def _get_landmarker() -> vision.FaceLandmarker:
    """
    전역 캐시(_LANDMARKER)를 사용해서 landmarker를 재사용
    - 처음 호출 때만 생성하고, 이후는 같은 객체를 돌려줌
    """
    global _LANDMARKER
    if _LANDMARKER is None:
        _LANDMARKER = build_face_landmarker(DEFAULT_MODEL_PATH)
    return _LANDMARKER


def run_visual(video_path: str) -> Dict[str, Any]:
    """
    최종 반환 포맷(v0 contract)에 맞춰 visual metric을 계산하는 메인 함수

    v0 Raw Output Contract:
    {
      "module": "visual",
      "metrics": {} or {face_presence_ratio, head_center_ratio, head_movement_std},
      "events": [],
      "error": null or {"type": "...", "message": "..."}
    }
    """
    try:
        # ------------------------------------------------------------
        # (2) 입력/환경 검증
        # ------------------------------------------------------------

        # video_path가 비어있거나 문자열이 아니면 에러
        if not video_path or not isinstance(video_path, str):
            return error_result(MODULE_NAME, "InvalidInput", "video_path is required (non-empty string).")

        # 실제 파일이 존재하는지 체크
        if not os.path.exists(video_path):
            return error_result(MODULE_NAME, "FileNotFound", f"video_path does not exist: {video_path}")

        # 모델 파일(.task) 존재 체크
        if not os.path.exists(DEFAULT_MODEL_PATH):
            return error_result(
                MODULE_NAME,
                "ModelNotFound",
                f"FaceLandmarker model (.task) not found: {DEFAULT_MODEL_PATH}",
            )

        # landmarker 로드(캐시)
        landmarker = _get_landmarker()

        # OpenCV로 비디오 열기
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return error_result(MODULE_NAME, "VideoOpenFailed", f"Failed to open video: {video_path}")

        # ------------------------------------------------------------
        # (3) 샘플링 설정
        # ------------------------------------------------------------

        # 원본 영상 FPS를 읽음
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        fps = float(fps) if fps > 0 else 30.0  # FPS를 못 읽으면 30으로 가정(안전한 기본값)

        # step: 몇 프레임마다 한 번 분석할지
        # 예) fps=30, TARGET_FPS=10 => step=3  (0,3,6,9...만 분석)
        step = max(1, int(round(fps / max(1, TARGET_FPS))))

        # ------------------------------------------------------------
        # (4) 프레임별로 쌓을 값들
        # ------------------------------------------------------------

        # 얼굴이 검출되었는지 기록(True/False)
        face_present: List[bool] = []

        # 얼굴이 검출된 경우 "코라고 가정한 랜드마크"의 x값(0~1 정규화)
        # 검출 실패 프레임은 None
        nose_x: List[Optional[float]] = []

        frame_idx = 0   # 전체 프레임 인덱스(0부터 증가)
        sampled = 0     # 실제로 분석한 샘플 수

        # ------------------------------------------------------------
        # (5) 비디오 프레임 루프
        # ------------------------------------------------------------
        while True:
            ret, frame = cap.read()  # 한 프레임 읽기
            if not ret:
                break  # 더 이상 읽을 프레임이 없음(EOF)

            # 샘플링: step에 안 맞으면 skip
            if frame_idx % step != 0:
                frame_idx += 1
                continue

            sampled += 1
            if sampled > MAX_SAMPLES:
                break  # 샘플 제한(너무 긴 영상 방지)

            # MediaPipe VIDEO 모드에서는 timestamp_ms가 필요함
            # - 프레임 인덱스와 fps로 대략적인 ms 타임스탬프 생성
            timestamp_ms = int((frame_idx / fps) * 1000)

            # OpenCV frame은 BGR, MediaPipe는 SRGB(RGB)를 기대하는 경우가 많음
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # MediaPipe가 받는 mp.Image 형식으로 래핑
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

            # FaceLandmarker 실행
            result = landmarker.detect_for_video(mp_image, timestamp_ms)

            # --------------------------------------------------------
            # (6) 얼굴 검출 여부 판단 기준
            # --------------------------------------------------------
            # 이 코드는 "얼굴이 있다"를
            # -> result.face_landmarks가 비어있지 않다(랜드마크가 나왔다)
            # 로 정의함.
            if result.face_landmarks:
                face_present.append(True)

                # 0번째 얼굴(우리는 num_faces=1이라 보통 0 하나만 존재)
                # NOSE_LANDMARK_IDX번째 랜드마크 점을 꺼냄
                # ⚠️ 현재 NOSE_LANDMARK_IDX=0이라 '0번 점'을 코라고 가정 중
                nose = result.face_landmarks[0][NOSE_LANDMARK_IDX]

                # nose.x는 정규화 좌표(0~1): 이미지 가로 위치 비율
                nose_x.append(float(nose.x))
            else:
                face_present.append(False)
                nose_x.append(None)

            frame_idx += 1  # 다음 프레임 인덱스로

        cap.release()  # 비디오 자원 해제

        if not face_present:
            # 샘플링 결과가 아예 없다면(영상이 깨졌거나 샘플링 로직 문제)
            return error_result(MODULE_NAME, "NoFrames", "No frames were processed from the video.")

        # ------------------------------------------------------------
        # (7) metric 계산
        # ------------------------------------------------------------

        # 7-1) face_presence_ratio
        # - 얼굴(랜드마크) 검출 성공 비율
        face_presence_ratio = _clamp01(sum(face_present) / len(face_present))

        # 7-2) head_center_ratio
        # - 얼굴이 잡힌 프레임에서만 nose_x를 보고,
        # - 그 값이 중앙 구간(lo~hi)에 들어온 비율
        lo, hi = NOSE_CENTER_RANGE
        valid_x = [v for v in nose_x if v is not None]

        head_center_ratio = _clamp01(
            (sum(1 for v in valid_x if lo <= v <= hi) / len(valid_x)) if valid_x else 0.0
        )

        # 7-3) head_movement_std
        # - 연속된 샘플에서 nose_x 변화량(Δx)을 계산
        # - 중간에 None(얼굴 미검출)이 끼면 prev를 None으로 리셋해서
        #   "결측 프레임을 건너뛰며 이어붙이는 왜곡"을 줄임
        diffs: List[float] = []
        prev: Optional[float] = None

        for v in nose_x:
            if v is None:
                prev = None      # 얼굴 끊기면 연결 끊기(연속성 보장)
                continue
            if prev is not None:
                diffs.append(abs(v - prev))  # 프레임 간 x변화량(좌우 이동량)
            prev = v

        # 변화량들의 표준편차: 움직임이 "불규칙/들쭉날쭉"할수록 커질 수 있음
        std_raw = float(np.std(diffs)) if diffs else 0.0

        # STD_REF로 나눠 0~1로 정규화(clamp)
        head_movement_std = _clamp01(std_raw / STD_REF)

        metrics = {
            "face_presence_ratio": float(face_presence_ratio),
            "head_center_ratio": float(head_center_ratio),
            "head_movement_std": float(head_movement_std),
        }

        return ok_result(MODULE_NAME, metrics=metrics, events=[])

    except Exception as e:
        # 예외 발생 시 error_result로 감싸서 반환
        return error_result(MODULE_NAME, type(e).__name__, str(e))
