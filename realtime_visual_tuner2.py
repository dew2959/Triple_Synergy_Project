import cv2
import numpy as np
import mediapipe as mp
import time
import os
import math
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# =========================================================
# ⚙️ 설정 및 상수 정의
# =========================================================
MODULE_NAME = "visual_tuner_final"
# 모델 경로 (본인의 프로젝트 경로에 맞게 수정 필요)
MODEL_PATH = os.path.join("app", "engines", "visual", "models", "face_landmarker.task")

# 1. 자세 (Posture)
NOSE_LANDMARK_IDX = 1       # 코 끝
HEAD_TOP_LANDMARK_IDX = 10  # 정수리
NOSE_CENTER_RANGE = (0.40, 0.60) # 중앙 인정 범위
STD_REF_ANGLE = 5.0         # 고개 기울임 허용 표준편차

# 2. 표정 (Expression)
SMILE_THRESHOLD = 0.5       # 미소 기준값

# 3. 긴장도 (Blink)
BLINK_THRESHOLD = 0.5       # 눈 감음 기준값

# 4. 시선 (Gaze)
# 왼쪽 눈
LEFT_EYE_INNER = 362
LEFT_EYE_OUTER = 263
LEFT_IRIS_CENTER = 468
# 오른쪽 눈
RIGHT_EYE_INNER = 33
RIGHT_EYE_OUTER = 133
RIGHT_IRIS_CENTER = 473
GAZE_THRESHOLD = 0.8  # 시선 이탈 기준 (0.0~1.0, 0.6 이상이면 이탈로 간주)


# =========================================================
# 🛠️ 유틸리티 함수
# =========================================================
def draw_text(img, text, x, y, color=(0, 255, 0), font_scale=0.6, thickness=2):
    cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), thickness+1)
    cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)

def draw_bar(img, x, y, w, h, val, max_val=1.0, color=(0, 255, 255), label=""):
    """게이지 바 그리기"""
    cv2.rectangle(img, (x, y), (x+w, y+h), (50, 50, 50), -1)
    ratio = max(0.0, min(1.0, val / max_val))
    fill_w = int(w * ratio)
    cv2.rectangle(img, (x, y), (x+fill_w, y+h), color, -1)
    cv2.rectangle(img, (x, y), (x+w, y+h), (200, 200, 200), 1)
    cv2.putText(img, f"{label}", (x, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

def calculate_angle(p1, p2):
    """정수리와 코를 잇는 선의 각도 계산 (Roll)"""
    dx = p1.x - p2.x
    dy = p1.y - p2.y
    return math.degrees(math.atan2(dy, dx)) + 90

def get_eye_gaze_score(face, inner_idx, outer_idx, iris_idx):
    """한쪽 눈의 시선 이탈 점수 계산"""
    p_inner = face[inner_idx]
    p_outer = face[outer_idx]
    p_iris = face[iris_idx]
    
    eye_width = abs(p_inner.x - p_outer.x)
    if eye_width == 0: return 0.0
    
    eye_center = (p_inner.x + p_outer.x) / 2.0
    dist_from_center = abs(p_iris.x - eye_center)
    
    # 정규화: (거리 / 눈동자반경) 느낌으로 변환. 
    # 보통 눈길이의 절반(0.5)을 넘어가면 완전 흰자위
    # 보정계수 2.5를 곱해 0~1 사이 스코어로 만듦
    score = (dist_from_center / (eye_width / 2.0)) * 2.5
    return score

# =========================================================
# 🚀 메인 실행 함수
# =========================================================
def main():
    if not os.path.exists(MODEL_PATH):
        print(f"❌ 모델 파일을 찾을 수 없습니다: {MODEL_PATH}")
        return

    # 모델 로드
    base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.FaceLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO,
        num_faces=1,
        output_face_blendshapes=True # 표정/깜빡임 필수
    )
    landmarker = vision.FaceLandmarker.create_from_options(options)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ 웹캠을 열 수 없습니다.")
        return

    print("✅ 종합 비주얼 튜너 시작! (종료: q)")

    # 데이터 저장소
    history_angles = []
    blink_count = 0
    prev_eye_closed = False
    start_time = time.time()
    
    # 시각 효과용
    blink_feedback_timer = 0

    while True:
        ret, frame = cap.read()
        if not ret: break

        # 1. 전처리 (좌우반전)
        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        timestamp_ms = int((time.time() - start_time) * 1000)
        
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = landmarker.detect_for_video(mp_image, timestamp_ms)

        # 초기값
        is_face = False
        nose_x_ratio = 0.5
        roll_angle = 0.0
        smile_score = 0.0
        blink_score = 0.0
        gaze_score = 0.0

        # =================================================
        # 🧠 분석 로직
        # =================================================
        if result.face_landmarks:
            is_face = True
            face = result.face_landmarks[0]
            
            # --- [1] 자세 (Posture) ---
            nose = face[NOSE_LANDMARK_IDX]
            head = face[HEAD_TOP_LANDMARK_IDX]
            nose_x_ratio = nose.x
            
            # 기울기 계산
            roll_angle = calculate_angle(head, nose)
            history_angles.append(roll_angle)
            if len(history_angles) > 30: history_angles.pop(0) # 최근 30프레임만 유지
            angle_std = np.std(history_angles) if len(history_angles) > 1 else 0.0

            # --- [2] 표정 & 깜빡임 (Blendshapes) ---
            if result.face_blendshapes:
                bs = result.face_blendshapes[0]
                
                # 미소
                s_l = next((x.score for x in bs if x.category_name=='mouthSmileLeft'), 0.0)
                s_r = next((x.score for x in bs if x.category_name=='mouthSmileRight'), 0.0)
                smile_score = (s_l + s_r) / 2.0
                
                # 깜빡임
                b_l = next((x.score for x in bs if x.category_name=='eyeBlinkLeft'), 0.0)
                b_r = next((x.score for x in bs if x.category_name=='eyeBlinkRight'), 0.0)
                blink_score = (b_l + b_r) / 2.0
                
                is_closed = blink_score > BLINK_THRESHOLD
                if is_closed and not prev_eye_closed:
                    blink_count += 1
                    blink_feedback_timer = 5 # 5프레임간 강조
                prev_eye_closed = is_closed

            # --- [3] 시선 (Gaze) ---
            g_left = get_eye_gaze_score(face, LEFT_EYE_INNER, LEFT_EYE_OUTER, LEFT_IRIS_CENTER)
            g_right = get_eye_gaze_score(face, RIGHT_EYE_INNER, RIGHT_EYE_OUTER, RIGHT_IRIS_CENTER)
            gaze_score = (g_left + g_right) / 2.0


            # =================================================
            # 🎨 화면 그리기 (Visual Debugging)
            # =================================================
            
            # 1. 중앙 가이드 박스
            box_color = (0, 255, 0) # Green
            if not (NOSE_CENTER_RANGE[0] <= nose_x_ratio <= NOSE_CENTER_RANGE[1]):
                box_color = (0, 0, 255) # Red (이탈)
            
            x1, x2 = int(w*NOSE_CENTER_RANGE[0]), int(w*NOSE_CENTER_RANGE[1])
            cv2.rectangle(frame, (x1, 0), (x2, h), box_color, 1)
            
            # 2. 얼굴 축 (기울기)
            pn = (int(nose.x*w), int(nose.y*h))
            ph = (int(head.x*w), int(head.y*h))
            line_col = (0, 255, 255) if abs(roll_angle) < 10 else (0, 0, 255)
            cv2.line(frame, pn, ph, line_col, 2)
            cv2.circle(frame, pn, 5, (0, 0, 255), -1)

            # 3. 눈동자 (시선)
            # 왼쪽 눈 시각화
            pil = (int(face[LEFT_IRIS_CENTER].x * w), int(face[LEFT_IRIS_CENTER].y * h))
            pir = (int(face[RIGHT_IRIS_CENTER].x * w), int(face[RIGHT_IRIS_CENTER].y * h))
            
            gaze_col = (0, 255, 0)
            if gaze_score > GAZE_THRESHOLD: gaze_col = (0, 0, 255) # 시선 이탈시 빨강
            
            cv2.circle(frame, pil, 3, gaze_col, -1)
            cv2.circle(frame, pir, 3, gaze_col, -1)
            
            # 시선 중앙 가이드라인 (눈높이)
            cv2.line(frame, (pil[0]-20, pil[1]), (pil[0]+20, pil[1]), (100,100,100), 1)
            cv2.line(frame, (pir[0]-20, pir[1]), (pir[0]+20, pir[1]), (100,100,100), 1)

        # =================================================
        # 📺 대시보드 (Dashboard) UI
        # =================================================
        # 패널 배경
        panel_w = 280
        cv2.rectangle(frame, (10, 10), (10+panel_w, 360), (0, 0, 0), -1)
        cv2.rectangle(frame, (10, 10), (10+panel_w, 360), (255, 255, 255), 1)
        
        y_cursor = 40
        gap = 30
        
        # [Header]
        status = "DETECTED" if is_face else "SEARCHING..."
        draw_text(frame, f"STATUS: {status}", 20, y_cursor, (0, 255, 0) if is_face else (0, 0, 255))
        y_cursor += 40

        # 1. 자세 (Position)
        pos_txt = "CENTER" if (NOSE_CENTER_RANGE[0] <= nose_x_ratio <= NOSE_CENTER_RANGE[1]) else "OFF-CENTER"
        col = (0, 255, 0) if pos_txt == "CENTER" else (0, 0, 255)
        draw_text(frame, f"1. Position: {pos_txt}", 20, y_cursor, col)
        y_cursor += gap
        
        # 2. 기울기 (Roll)
        roll_txt = f"{roll_angle:.1f} deg"
        col = (0, 255, 0) if abs(roll_angle) < 10 else (0, 0, 255)
        draw_text(frame, f"2. Head Roll: {roll_txt}", 20, y_cursor, col)
        draw_bar(frame, 180, y_cursor-15, 80, 10, abs(roll_angle), 20.0, col)
        y_cursor += gap
        
        # 3. 움직임 (Stability)
        std_txt = f"Stable ({angle_std:.1f})" if angle_std < STD_REF_ANGLE else f"Shaky ({angle_std:.1f})"
        col = (0, 255, 0) if angle_std < STD_REF_ANGLE else (0, 0, 255)
        draw_text(frame, f"3. Stability: {std_txt}", 20, y_cursor, col)
        y_cursor += gap + 10

        # 4. 시선 (Gaze)
        print(gaze_score)
        gaze_state = "GOOD" if gaze_score < GAZE_THRESHOLD else "BAD"
        col = (0, 255, 0) if gaze_state == "GOOD" else (0, 0, 255)
        draw_text(frame, f"4. Eye Contact: {gaze_state}", 20, y_cursor, col)
        draw_bar(frame, 180, y_cursor-15, 80, 10, gaze_score, 1.0, col)
        y_cursor += gap

        # 5. 미소 (Smile)
        smile_state = "Smiling" if smile_score > SMILE_THRESHOLD else "Neutral"
        col = (255, 255, 0) if smile_score > SMILE_THRESHOLD else (200, 200, 200)
        draw_text(frame, f"5. Smile: {smile_state}", 20, y_cursor, col)
        draw_bar(frame, 180, y_cursor-15, 80, 10, smile_score, 1.0, col)
        y_cursor += gap

        # 6. 깜빡임 (Blink)
        bpm = (blink_count / ((time.time()-start_time)/60)) if (time.time()-start_time) > 1 else 0
        blink_col = (0, 255, 255) if blink_feedback_timer > 0 else (200, 200, 200)
        draw_text(frame, f"6. Blinks: {blink_count} ({bpm:.0f}/m)", 20, y_cursor, blink_col)
        
        if blink_feedback_timer > 0:
            blink_feedback_timer -= 1
            cv2.circle(frame, (260, y_cursor-5), 8, (0, 255, 255), -1)

        cv2.imshow('Final Visual Tuner', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    landmarker.close()

if __name__ == "__main__":
    main()