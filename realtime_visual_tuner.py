import cv2
import numpy as np
import mediapipe as mp
import time
import os
import math
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# =========================================================
# ⚙️ 설정 및 상수
# =========================================================
# 모델 경로 (본인 환경에 맞게 수정 필요)
MODEL_PATH = os.path.join("app", "engines", "visual", "models", "face_landmarker.task")

# 화면 설정
MIRROR_VIEW = True  # 거울 모드

# --- 임계값 설정 ---
# 1. Head
HEAD_NORMAL_LIMIT = 2.5   # 정상 범위 (도)
HEAD_MAJOR_LIMIT = 10.0   # 심각한 이탈 기준 (도)
HEAD_TIME_LIMIT = 3.0     # 경미한 이탈 허용 시간 (초)

# 2. Blink
BLINK_THRESH = 0.5        # 눈 감음 판정 Score
BPM_MIN = 10              # 정상 최소 BPM
BPM_MAX = 30              # 정상 최대 BPM

# 3. Smile
SMILE_THRESH = 0.5        # 미소 판정 Score

# 4. Gaze (Iris)
GAZE_ENTER = 0.18
GAZE_EXIT = 0.10
L_OUTER, L_INNER = 33, 133
R_OUTER, R_INNER = 263, 362
L_IRIS = [468, 469, 470, 471, 472]
R_IRIS = [473, 474, 475, 476, 477]

# =========================================================
# 🛠️ 유틸리티 함수
# =========================================================
def _lm_px(lm, w, h):
    return np.array([lm.x * w, lm.y * h], dtype=np.float32)

def _iris_center(landmarks, w, h, idxs):
    pts = []
    for i in idxs:
        pts.append(_lm_px(landmarks[i], w, h))
    return np.mean(np.stack(pts, axis=0), axis=0)

def _eye_axis(landmarks, w, h, outer_idx, inner_idx):
    p_outer = _lm_px(landmarks[outer_idx], w, h)
    p_inner = _lm_px(landmarks[inner_idx], w, h)
    eye_center = (p_outer + p_inner) * 0.5
    v = (p_inner - p_outer)
    norm = np.linalg.norm(v) + 1e-6
    u = v / norm
    return eye_center, u, norm

def _iris_shift_1d(iris_c, eye_center, eye_u, eye_width):
    rel = iris_c - eye_center
    shift = float(np.dot(rel, eye_u)) / max(eye_width, 1.0)
    return shift

def calculate_roll(p1, p2):
    # p1: Head(10), p2: Nose(1)
    dx = p1.x - p2.x
    dy = p1.y - p2.y
    angle_deg = math.degrees(math.atan2(dy, dx)) + 90
    return angle_deg

def draw_korean_text(img, text, pos, color, scale=0.6):
    # OpenCV는 한글 지원이 안되므로 영문으로 대체하거나, PIL을 써야 함.
    # 여기서는 빠른 실행을 위해 영문 표기 + 콘솔 로그를 가정.
    cv2.putText(img, text, pos, cv2.FONT_HERSHEY_SIMPLEX, scale, color, 2)

# =========================================================
# 🧠 분석 클래스 (상태 관리)
# =========================================================
class InterviewAnalyzer:
    def __init__(self):
        self.start_time = time.time()
        
        # --- Head State ---
        self.score_head = 50
        self.head_violations = {
            "short_minor": 0, # 3초 이하, 2.5~10도
            "long_minor": 0,  # 3초 초과, 2.5~10도
            "major": 0        # 10도 이상
        }
        self.curr_head_start = None
        self.curr_head_max_angle = 0.0
        self.is_head_deviated = False

        # --- Smile State ---
        self.score_smile = 0 # 기본 0 (한번이라도 웃으면 5)
        self.has_smiled = False

        # --- Blink State ---
        self.score_blink = 10
        self.blink_count = 0
        self.is_eye_closed = False
        self.bad_bpm_duration = 0.0 # BPM이 비정상이었던 누적 시간
        self.prev_bpm_status = "NORMAL" # NORMAL, FAST, SLOW

        # --- Gaze State ---
        self.score_gaze = 20
        self.base_L = None
        self.base_R = None
        self.calib_samples = []
        self.gaze_state = "CENTER"
        self.gaze_off_start = None
        self.total_gaze_off_time = 0.0
        self.long_gaze_off_count = 0 # 2초 초과 이탈 횟수

        # --- Global ---
        self.base_score = 15

    def update(self, landmarks, blendshapes, w, h):
        now = time.time()
        elapsed = now - self.start_time
        if elapsed < 0.1: return # 시작 직후 스킵

        # ---------------------------
        # 1. Head Analysis
        # ---------------------------
        nose = landmarks[1]
        head_top = landmarks[10]
        roll = calculate_roll(head_top, nose)
        abs_roll = abs(roll)

        if abs_roll > HEAD_NORMAL_LIMIT:
            if not self.is_head_deviated:
                self.is_head_deviated = True
                self.curr_head_start = now
                self.curr_head_max_angle = abs_roll
            else:
                self.curr_head_max_angle = max(self.curr_head_max_angle, abs_roll)
        else:
            if self.is_head_deviated:
                # 이탈 종료 -> 평가
                duration = now - self.curr_head_start
                max_angle = self.curr_head_max_angle
                
                if max_angle > HEAD_MAJOR_LIMIT:
                    self.head_violations["major"] += 1
                elif duration > HEAD_TIME_LIMIT:
                    self.head_violations["long_minor"] += 1
                else:
                    self.head_violations["short_minor"] += 1
                
                self.is_head_deviated = False

        # Head Score Calculation
        deduction_head = 0
        # (1) Short Minor: 3회 무료, 4회부터 회당 -5
        deduction_head += max(0, self.head_violations["short_minor"] - 3) * 5
        # (2) Long Minor: 회당 -10
        deduction_head += self.head_violations["long_minor"] * 10
        # (3) Major: 1회 무료, 2회부터 회당 -20
        deduction_head += max(0, self.head_violations["major"] - 1) * 20
        
        self.score_head = max(0, 50 - min(50, deduction_head))

        # ---------------------------
        # 2. Smile Analysis
        # ---------------------------
        smile_score = 0.0
        if blendshapes:
            s_left = next((x.score for x in blendshapes if x.category_name == 'mouthSmileLeft'), 0.0)
            s_right = next((x.score for x in blendshapes if x.category_name == 'mouthSmileRight'), 0.0)
            smile_score = (s_left + s_right) / 2.0
        
        if smile_score > SMILE_THRESH:
            self.has_smiled = True
        
        self.score_smile = 5 if self.has_smiled else 0

        # ---------------------------
        # 3. Blink Analysis
        # ---------------------------
        eye_score = 0.0
        if blendshapes:
            b_left = next((x.score for x in blendshapes if x.category_name == 'eyeBlinkLeft'), 0.0)
            b_right = next((x.score for x in blendshapes if x.category_name == 'eyeBlinkRight'), 0.0)
            eye_score = (b_left + b_right) / 2.0

        is_closed = eye_score > BLINK_THRESH
        if is_closed and not self.is_eye_closed:
            self.blink_count += 1
        self.is_eye_closed = is_closed

        # BPM 계산 및 상태 누적
        bpm = self.blink_count / (elapsed / 60.0) if elapsed > 1 else 0
        
        bpm_status = "NORMAL"
        if elapsed > 5: # 5초 이후부터 판정
            if bpm > BPM_MAX: bpm_status = "FAST"
            elif bpm < BPM_MIN: bpm_status = "SLOW"
        
        if bpm_status != "NORMAL":
            # 이전 프레임 시간차(약 0.033초)만큼 누적
            # 정확도를 위해 실제 dt를 쓰면 좋지만 여기선 근사치
            self.bad_bpm_duration += 0.033 

        # Blink Score Calc
        # 비정상 비율 계산
        bad_ratio = self.bad_bpm_duration / elapsed
        blink_deduction = 0
        if bad_ratio >= 0.1: # 10% 이상 비정상이면 부분 감점
            blink_deduction = 5
        if bad_ratio > 0.5: # 50% 이상(전체적으로) 비정상이면 추가 감점 -> 총 10점
            blink_deduction = 10
        
        # 최대 감점 -15 제한이 있지만 항목 만점이 10점이므로 0점 하한선
        self.score_blink = max(0, 10 - blink_deduction)


        # ---------------------------
        # 4. Gaze Analysis
        # ---------------------------
        # (Iris tracking logic from snippet)
        iris_L = _iris_center(landmarks, w, h, L_IRIS)
        iris_R = _iris_center(landmarks, w, h, R_IRIS)
        
        label_gaze = "N/A"
        
        if iris_L is not None and iris_R is not None:
            cL, uL, wL = _eye_axis(landmarks, w, h, L_OUTER, L_INNER)
            cR, uR, wR = _eye_axis(landmarks, w, h, R_OUTER, R_INNER)
            sL = _iris_shift_1d(iris_L, cL, uL, wL)
            sR = _iris_shift_1d(iris_R, cR, uR, wR)

            if len(self.calib_samples) < 30:
                self.calib_samples.append((sL, sR))
                if len(self.calib_samples) == 30:
                    self.base_L = sum(x for x, _ in self.calib_samples) / 30
                    self.base_R = sum(y for _, y in self.calib_samples) / 30
                label_gaze = "CALIB"
            else:
                dL = sL - self.base_L
                dR = sR - self.base_R
                d = dL if abs(dL) >= abs(dR) else dR
                if MIRROR_VIEW: d = -d # 거울모드 보정

                # State Machine
                if self.gaze_state == "CENTER":
                    if d > GAZE_ENTER: 
                        self.gaze_state = "RIGHT"
                        self.gaze_off_start = now
                    elif d < -GAZE_ENTER: 
                        self.gaze_state = "LEFT"
                        self.gaze_off_start = now
                else:
                    if abs(d) < GAZE_EXIT:
                        # 이탈 종료 -> 시간 계산
                        if self.gaze_off_start:
                            off_dur = now - self.gaze_off_start
                            self.total_gaze_off_time += off_dur
                            if off_dur > 2.0: # 2초 초과 이탈
                                self.long_gaze_off_count += 1
                        self.gaze_state = "CENTER"
                        self.gaze_off_start = None
                    else:
                        # 이탈 중 -> 현재 시간도 누적에 포함(실시간성을 위해)
                        pass
                
                label_gaze = self.gaze_state

        # Gaze Score Calc
        gaze_deduction = 0
        
        # (1) 전체 시간의 10% 이상 이탈
        # 현재 진행중인 이탈 시간도 합산
        current_off_add = 0
        if self.gaze_state != "CENTER" and self.gaze_off_start:
            current_off_add = now - self.gaze_off_start
        
        total_off_ratio = (self.total_gaze_off_time + current_off_add) / max(elapsed, 1)
        if total_off_ratio >= 0.10:
            gaze_deduction += 10
        
        # (2) 2초 초과 이탈 횟수 (회당 -5, 최대 -10)
        long_off_deduction = min(10, self.long_gaze_off_count * 5)
        gaze_deduction += long_off_deduction

        self.score_gaze = max(0, 20 - gaze_deduction)

        return {
            "roll": roll,
            "bpm": bpm,
            "gaze": label_gaze,
            "total_score": self.base_score + self.score_head + self.score_smile + self.score_blink + self.score_gaze,
            "scores": (self.score_head, self.score_smile, self.score_blink, self.score_gaze),
            "counts": (self.head_violations, self.blink_count, self.long_gaze_off_count)
        }

# =========================================================
# 🚀 메인 실행
# =========================================================
def main():
    if not os.path.exists(MODEL_PATH):
        print(f"❌ 모델 없음: {MODEL_PATH}")
        return

    base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.FaceLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO,
        num_faces=1,
        output_face_blendshapes=True
    )
    landmarker = vision.FaceLandmarker.create_from_options(options)

    cap = cv2.VideoCapture(0)
    analyzer = InterviewAnalyzer()

    while True:
        ret, frame = cap.read()
        if not ret: break
        
        if MIRROR_VIEW: frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        ts = int((time.time() - analyzer.start_time) * 1000)

        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = landmarker.detect_for_video(mp_image, ts)

        data = None
        if result.face_landmarks:
            lm = result.face_landmarks[0]
            bs = result.face_blendshapes[0]
            data = analyzer.update(lm, bs, w, h)
            
            # --- 시각화 ---
            # 1. 랜드마크 그리기 (코, 정수리, 눈)
            nose = _lm_px(lm[1], w, h)
            head = _lm_px(lm[10], w, h)
            cv2.line(frame, (int(nose[0]), int(nose[1])), (int(head[0]), int(head[1])), (0, 255, 255), 2)
            
            # 2. 정보 패널
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (350, h), (0, 0, 0), -1)
            frame = cv2.addWeighted(overlay, 0.6, frame, 0.4, 0)
            
            s_head, s_smile, s_blink, s_gaze = data["scores"]
            violations, blinks, gaze_long = data["counts"]
            
            y = 40
            draw_korean_text(frame, f"TOTAL: {int(data['total_score'])}/100", (10, y), (0, 255, 0), 1.0)
            
            y += 40
            col = (255, 255, 255)
            draw_korean_text(frame, f"[Head] {s_head}/50 (Ang:{data['roll']:.1f})", (10, y), col)
            y += 25
            draw_korean_text(frame, f" - Short(>3): {violations['short_minor']}", (20, y), (200, 200, 200), 0.5)
            y += 20
            draw_korean_text(frame, f" - Long(>3s): {violations['long_minor']}", (20, y), (200, 200, 200), 0.5)
            y += 20
            draw_korean_text(frame, f" - Major(>10): {violations['major']}", (20, y), (200, 200, 200), 0.5)

            y += 40
            draw_korean_text(frame, f"[Smile] {s_smile}/5", (10, y), col)
            y += 25
            status = "SMILED!" if s_smile > 0 else "NO SMILE"
            draw_korean_text(frame, f" - {status}", (20, y), (200, 200, 200), 0.5)

            y += 40
            draw_korean_text(frame, f"[Blink] {s_blink}/10 (BPM:{data['bpm']:.1f})", (10, y), col)
            y += 25
            draw_korean_text(frame, f" - Count: {blinks}", (20, y), (200, 200, 200), 0.5)

            y += 40
            draw_korean_text(frame, f"[Gaze] {s_gaze}/20 ({data['gaze']})", (10, y), col)
            y += 25
            draw_korean_text(frame, f" - Long Off(>2s): {gaze_long}", (20, y), (200, 200, 200), 0.5)

        else:
            cv2.putText(frame, "NO FACE", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        cv2.imshow("Interview AI Analyst", frame)
        if cv2.waitKey(1) & 0xFF == 27: break

    cap.release()
    cv2.destroyAllWindows()
    landmarker.close()

if __name__ == "__main__":
    main()