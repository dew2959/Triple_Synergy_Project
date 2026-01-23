import cv2
import numpy as np
import mediapipe as mp
import time
import os
from collections import deque
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# =========================================================
# ⚙️ 설정 및 상수 (engine.py와 동일하게 맞춤)
# =========================================================
MODULE_NAME = "visual_tuner"
# 모델 경로: 프로젝트 구조에 맞춰 설정 (실행 위치 기준)
MODEL_PATH = os.path.join("app", "engines", "visual", "models", "face_landmarker.task")

NOSE_CENTER_RANGE = (0.40, 0.60)  # 중앙 인정 범위 (40% ~ 60%)
STD_REF = 0.02                    # 고개 움직임 기준값
NOSE_LANDMARK_IDX = 0             # 코 끝 랜드마크 인덱스

# =========================================================
# 🛠️ 유틸리티 함수
# =========================================================
def _clamp01(x: float) -> float:
    return float(max(0.0, min(1.0, x)))

def draw_text(img, text, x, y, color=(0, 255, 0), font_scale=0.6):
    cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), 3) # 그림자
    cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, 2)

def main():
    if not os.path.exists(MODEL_PATH):
        print(f"❌ 모델 파일을 찾을 수 없습니다: {MODEL_PATH}")
        print("   app/engines/visual/models/ 폴더에 face_landmarker.task 파일이 있는지 확인해주세요.")
        return

    # 1. Face Landmarker 초기화
    base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.FaceLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO, # 웹캠 스트림 처리를 위해 VIDEO 모드 사용 (프레임 순차 주입)
        num_faces=1,
        output_face_blendshapes=False,
        output_facial_transformation_matrixes=False,
    )
    landmarker = vision.FaceLandmarker.create_from_options(options)

    # 2. 웹캠 실행
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ 웹캠을 열 수 없습니다.")
        return

    print("✅ 실시간 분석 시작! (종료하려면 'q'를 누르세요)")

    # 3. 데이터 누적 변수 (세션 전체 평균 계산용)
    history_face_present = []
    history_nose_x = []
    history_diffs = [] # 움직임 표준편차 계산용
    
    prev_nose_x = None
    start_time = time.time()

    # 프레임 루프
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # 미러링 (거울 모드)
        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 현재 시간 (ms)
        timestamp_ms = int((time.time() - start_time) * 1000)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        # ------------------------------------------------
        # 🔍 감지 실행
        # ------------------------------------------------
        result = landmarker.detect_for_video(mp_image, timestamp_ms)

        current_nose_x = None
        is_face_present = False

        if result.face_landmarks:
            is_face_present = True
            nose = result.face_landmarks[0][NOSE_LANDMARK_IDX]
            current_nose_x = nose.x # 0.0 ~ 1.0 정규화된 좌표
            
            # 화면 그리기 (코 위치)
            pixel_x, pixel_y = int(nose.x * w), int(nose.y * h)
            cv2.circle(frame, (pixel_x, pixel_y), 8, (0, 0, 255), -1) # 빨간 점
            
            # 중앙 범위 박스 그리기 (녹색 박스)
            x1, x2 = int(w * NOSE_CENTER_RANGE[0]), int(w * NOSE_CENTER_RANGE[1])
            overlay = frame.copy()
            cv2.rectangle(overlay, (x1, 0), (x2, h), (0, 255, 0), -1)
            cv2.addWeighted(overlay, 0.2, frame, 0.8, 0, frame) # 투명하게 표시

        # ------------------------------------------------
        # 📊 지표 실시간 계산 (누적 데이터 기반)
        # ------------------------------------------------
        history_face_present.append(is_face_present)
        history_nose_x.append(current_nose_x)

        # 움직임 차이 계산
        if current_nose_x is not None:
            if prev_nose_x is not None:
                diff = abs(current_nose_x - prev_nose_x)
                history_diffs.append(diff)
            prev_nose_x = current_nose_x
        else:
            prev_nose_x = None # 얼굴 놓치면 흐름 끊기

        # (1) 화면 응시율 (Face Presence Ratio)
        metrics_presence = sum(history_face_present) / len(history_face_present) if history_face_present else 0.0
        
        # (2) 중앙 유지율 (Head Center Ratio) - 얼굴이 감지된 프레임 중 중앙에 있는 비율
        valid_x = [x for x in history_nose_x if x is not None]
        center_count = sum(1 for x in valid_x if NOSE_CENTER_RANGE[0] <= x <= NOSE_CENTER_RANGE[1])
        metrics_center = center_count / len(valid_x) if valid_x else 0.0

        # (3) 고개 움직임 (Head Movement STD)
        std_raw = np.std(history_diffs) if history_diffs else 0.0
        metrics_movement = _clamp01(float(std_raw) / STD_REF)

        # ------------------------------------------------
        # 📺 화면에 정보 출력
        # ------------------------------------------------
        # 상태 패널 배경
        cv2.rectangle(frame, (10, 10), (450, 180), (0, 0, 0), -1) # 검은 배경
        
        # 현재 상태 표시
        status_color = (0, 255, 0) if is_face_present else (0, 0, 255)
        status_text = f"Face: {'DETECTED' if is_face_present else 'LOST'}"
        draw_text(frame, status_text, 30, 40, status_color)
        
        if current_nose_x:
            nose_text = f"Nose X: {current_nose_x:.3f} ({'CENTER' if NOSE_CENTER_RANGE[0]<=current_nose_x<=NOSE_CENTER_RANGE[1] else 'OUT'})"
            draw_text(frame, nose_text, 250, 40, (255, 255, 0))

        # 누적 지표 (engine.py 로직과 동일)
        cv2.line(frame, (20, 55), (440, 55), (255, 255, 255), 1)
        
        # 1. Presence Ratio
        p_color = (0, 255, 0) if metrics_presence >= 0.8 else (0, 0, 255)
        draw_text(frame, f"1. Presence Ratio: {metrics_presence:.3f} (Target > 0.8)", 30, 80, p_color)

        # 2. Center Ratio
        c_color = (0, 255, 0) if metrics_center >= 0.6 else (0, 0, 255)
        draw_text(frame, f"2. Center Ratio  : {metrics_center:.3f} (Target > 0.6)", 30, 115, c_color)

        # 3. Movement STD
        # 낮을수록 좋음 (0에 가까우면 안정적)
        m_color = (0, 255, 0) if metrics_movement < 0.3 else (0, 0, 255) # 임의 기준 0.3
        draw_text(frame, f"3. Movement STD  : {metrics_movement:.3f} (Low is Better)", 30, 150, m_color)


        cv2.imshow('Visual Metrics Tuner', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    landmarker.close()

if __name__ == "__main__":
    main()