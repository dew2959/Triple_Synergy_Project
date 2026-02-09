import os
import cv2
import math
import numpy as np
import mediapipe as mp
from typing import Dict, Any, List
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# 프로젝트 설정 (필요 시 사용)
from app.core.config import settings

# =========================================================
# ⚙️ V3 채점 기준 상수 설정
# =========================================================
# [1] Head (고개 각도)
HEAD_NORMAL_THRESHOLD = 2.5   # 정상 범위 (±2.5도)
HEAD_MINOR_THRESHOLD = 10.0   # 경미/심각 경계 (10도)
HEAD_MINOR_TIME_LIMIT = 3.0   # 경미한 이탈 허용 시간 (3초)
HEAD_MINOR_ALLOW_COUNT = 3    # 경미한 이탈 허용 횟수
HEAD_MAJOR_ALLOW_COUNT = 1    # 심각한 이탈 허용 횟수

# [2] Smile (미소)
SMILE_THRESHOLD = 0.5         # 미소 감지 임계값 (Blendshape)

# [3] Blink (눈 깜빡임)
BLINK_THRESHOLD = 0.5         # 눈 감음 임계값
BLINK_RPM_MIN = 10            # 정상 최소 RPM
BLINK_RPM_MAX = 30            # 정상 최대 RPM

# [4] Gaze (시선)
GAZE_OFF_RATIO_LIMIT = 0.10   # 전체 시간 대비 허용 이탈 비율 (10%)
GAZE_LONG_DURATION = 2.0      # 장기 이탈 기준 시간 (2초)

# MediaPipe 모델 경로
MODEL_PATH = os.path.join(os.getcwd(), "app", "engines", "visual", "models", "face_landmarker.task")

class VisualAnalysisEngine:
    def __init__(self):
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"MediaPipe Model not found at: {MODEL_PATH}")

    # ---------------------------------------------------------
    # 📐 수학/기하학 유틸리티 함수
    # ---------------------------------------------------------
    def _calculate_head_angle(self, p_nose, p_head) -> float:
        """코(Nose)와 정수리(HeadTop) 좌표를 이용해 고개 기울기(Roll) 계산"""
        dx = p_head.x - p_nose.x
        dy = p_head.y - p_nose.y
        # 영상 좌표계(y가 아래로) 고려
        angle_rad = math.atan2(dy, dx)
        angle_deg = math.degrees(angle_rad) + 90
        return angle_deg

    def _get_iris_shift(self, landmarks, w, h) -> float:
        """눈동자(Iris) 위치를 기반으로 시선 이탈 정도 계산"""
        # 랜드마크 인덱스
        L_OUTER, L_INNER = 33, 133
        R_OUTER, R_INNER = 263, 362
        L_IRIS = [468, 469, 470, 471, 472]
        R_IRIS = [473, 474, 475, 476, 477]

        def _to_px(lm): return np.array([lm.x * w, lm.y * h])
        
        def _get_center(idxs):
            pts = [_to_px(landmarks[i]) for i in idxs]
            return np.mean(pts, axis=0)

        def _calc_shift(iris_c, outer_idx, inner_idx):
            p_out = _to_px(landmarks[outer_idx])
            p_in = _to_px(landmarks[inner_idx])
            eye_width = np.linalg.norm(p_in - p_out) + 1e-6
            eye_center = (p_out + p_in) * 0.5
            eye_vec = (p_in - p_out) / eye_width
            
            # 투영(Projection)을 통해 중심으로부터 거리 계산
            rel = iris_c - eye_center
            shift = float(np.dot(rel, eye_vec)) / eye_width
            return shift

        try:
            iris_l_c = _get_center(L_IRIS)
            iris_r_c = _get_center(R_IRIS)
            
            shift_l = _calc_shift(iris_l_c, L_OUTER, L_INNER)
            shift_r = _calc_shift(iris_r_c, R_OUTER, R_INNER)
            
            # 두 눈 중 더 크게 이탈한 값을 반환
            return max(abs(shift_l), abs(shift_r))
        except:
            return 0.0

    # ---------------------------------------------------------
    # 🚀 메인 분석 로직
    # ---------------------------------------------------------
    def analyze(self, video_path: str) -> Dict[str, Any]:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return {"error": "Failed to open video file"}
        base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO, # 비디오 모드
            num_faces=1,
            output_face_blendshapes=True,
            output_facial_transformation_matrixes=True
        )
        landmarker = vision.FaceLandmarker.create_from_options(options)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_sec = frame_count / fps if fps > 0 else 0

        # 시계열 데이터 저장소
        history = {
            "timestamps": [],
            "head_angles": [],
            "gaze_shifts": [],
            "blink_scores": [],
            "smile_scores": []
        }
        try :
            # 1️⃣ 프레임 단위 데이터 추출
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                timestamp_ms = int(cap.get(cv2.CAP_PROP_POS_MSEC))
                h, w, _ = frame.shape
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

                result = landmarker.detect_for_video(mp_img, timestamp_ms)

                # 기본값 (감지 안될 경우)
                angle = 0.0
                gaze_shift = 0.0
                blink_sc = 0.0
                smile_sc = 0.0

                if result.face_landmarks:
                    landmarks = result.face_landmarks[0]
                    blendshapes = result.face_blendshapes[0]

                    # (1) Head Angle
                    nose = landmarks[1]
                    head_top = landmarks[10]
                    angle = self._calculate_head_angle(nose, head_top)

                    # (2) Gaze Shift
                    gaze_shift = self._get_iris_shift(landmarks, w, h)

                    # (3) Blendshapes (Blink & Smile)
                    # MediaPipe Blendshape 이름 매핑
                    bs_dict = {b.category_name: b.score for b in blendshapes}
                    blink_sc = (bs_dict.get('eyeBlinkLeft', 0) + bs_dict.get('eyeBlinkRight', 0)) / 2.0
                    smile_sc = (bs_dict.get('mouthSmileLeft', 0) + bs_dict.get('mouthSmileRight', 0)) / 2.0

                history["timestamps"].append(timestamp_ms / 1000.0) # sec
                history["head_angles"].append(angle)
                history["gaze_shifts"].append(gaze_shift)
                history["blink_scores"].append(blink_sc)
                history["smile_scores"].append(smile_sc)

        except Exception as e:
            print(f"MediaPipe Process Error: {e}")
            return {"error": str(e)}
        
        finally:
            # 🟢 [수정 3] 사용 후 반드시 리소스 해제
            cap.release()
            landmarker.close()

        # 2️⃣ V3 채점 로직 적용
        return self._calculate_v3_score(history, duration_sec)

    def _calculate_v3_score(self, h: Dict[str, List[float]], duration: float) -> Dict[str, Any]:
        if duration <= 0:
            return {"score": 0, "feedback": "영상 길이가 너무 짧습니다."}

        # --- 점수판 초기화 ---
        scores = {
            "head": 50,
            "smile": 0,  # 기본 0, 감지시 +5
            "blink": 10,
            "gaze": 20,
            "base": 15
        }
        deductions = [] # 감점 사유 기록

        # =========================================================
        # [1] Head Logic (50점 만점)
        # =========================================================
        # 2.5도 ~ 10도 (Minor), 10도 이상 (Major)
        minor_events = [] # duration list
        major_events = [] # duration list
        
        curr_state = "NORMAL" # NORMAL, MINOR, MAJOR
        start_time = 0
        
        times = h["timestamps"]
        angles = h["head_angles"]

        for i, t in enumerate(times):
            abs_ang = abs(angles[i])
            
            # 상태 판단
            if abs_ang >= HEAD_MINOR_THRESHOLD:
                new_state = "MAJOR"
            elif abs_ang >= HEAD_NORMAL_THRESHOLD:
                new_state = "MINOR"
            else:
                new_state = "NORMAL"

            # 상태 변화 처리 (이벤트 종료 및 기록)
            if new_state != curr_state:
                if curr_state != "NORMAL":
                    dur = t - start_time
                    if curr_state == "MINOR": minor_events.append(dur)
                    if curr_state == "MAJOR": major_events.append(dur)
                
                start_time = t
                curr_state = new_state
        
        # 마지막 상태 처리
        if curr_state != "NORMAL":
            dur = times[-1] - start_time
            if curr_state == "MINOR": minor_events.append(dur)
            if curr_state == "MAJOR": major_events.append(dur)

        # -- Head 점수 계산 --
        head_deduction = 0
        
        # Minor Logic: 3초 초과 -> 즉시 -10 (불안정). 3초 이하 -> 3회 허용 후 -5/회
        minor_short_count = 0
        for dur in minor_events:
            if dur > HEAD_MINOR_TIME_LIMIT:
                head_deduction += 10
                deductions.append(f"고개 경미 이탈 3초 이상 지속 (-10점)")
            else:
                minor_short_count += 1
        
        if minor_short_count > HEAD_MINOR_ALLOW_COUNT:
            penalty_count = minor_short_count - HEAD_MINOR_ALLOW_COUNT
            ded = penalty_count * 5
            head_deduction += ded
            deductions.append(f"고개 경미 이탈 횟수 초과({penalty_count}회) (-{ded}점)")

        # Major Logic: 1회 허용, 이후 -20/회
        if len(major_events) > HEAD_MAJOR_ALLOW_COUNT:
            penalty_count = len(major_events) - HEAD_MAJOR_ALLOW_COUNT
            ded = penalty_count * 20
            head_deduction += ded
            deductions.append(f"고개 심각한 이탈 횟수 초과({penalty_count}회) (-{ded}점)")

        # 최대 감점 -50
        scores["head"] = max(0, 50 - min(50, head_deduction))


        # =========================================================
        # [2] Smile Logic (5점 만점)
        # =========================================================
        # 한번이라도 0.5 이상이면 +5
        max_smile = max(h["smile_scores"]) if h["smile_scores"] else 0
        if max_smile >= SMILE_THRESHOLD:
            scores["smile"] = 5
        else:
            deductions.append("미소가 감지되지 않음 (0/5점)")


        # =========================================================
        # [3] Blink Logic (10점 만점)
        # =========================================================
        # Blink Count (Rising Edge 감지)
        blink_cnt = 0
        is_closed = False
        for s in h["blink_scores"]:
            if s > BLINK_THRESHOLD:
                if not is_closed:
                    blink_cnt += 1
                    is_closed = True
            else:
                is_closed = False
        
        rpm = blink_cnt / (duration / 60.0) if duration > 0 else 0
        
        if rpm < BLINK_RPM_MIN: # 너무 적게 깜빡임 (긴장/경직)
            if rpm < 5: # 심각
                scores["blink"] -= 10
                deductions.append(f"눈 깜빡임이 매우 부족함({rpm:.1f}회/분) (-10점)")
            else:
                scores["blink"] -= 5
                deductions.append(f"눈 깜빡임 부족({rpm:.1f}회/분) (-5점)")
        elif rpm > BLINK_RPM_MAX: # 너무 많이 깜빡임 (불안)
            if rpm > 50: # 심각
                scores["blink"] -= 10
                deductions.append(f"눈 깜빡임이 과도함({rpm:.1f}회/분) (-10점)")
            else:
                scores["blink"] -= 5
                deductions.append(f"눈 깜빡임 다소 과함({rpm:.1f}회/분) (-5점)")
        
        scores["blink"] = max(0, scores["blink"]) # 0점 미만 방지


        # =========================================================
        # [4] Gaze Logic (20점 만점)
        # =========================================================
        GAZE_THRESH = 0.15 # 튜닝값 (이 정도 shift면 이탈로 간주)
        
        gaze_off_frames = 0
        long_gaze_events = 0
        current_gaze_dur = 0
        
        for shift in h["gaze_shifts"]:
            if shift > GAZE_THRESH:
                gaze_off_frames += 1
                current_gaze_dur += 1
            else:
                # 이탈 종료 시 장기 여부 체크
                if current_gaze_dur > 0:
                    # 프레임 수 -> 시간 변환 필요 (여기선 약식으로 프레임간격 평균 사용)
                    # 정확히 하려면 timestamp 참조해야 함. 약식 로직:
                    dt = duration / len(h["timestamps"])
                    sec = current_gaze_dur * dt
                    if sec > GAZE_LONG_DURATION:
                        long_gaze_events += 1
                current_gaze_dur = 0
        
        total_score = 100
        # 점수 계산
        ratio = gaze_off_frames / len(h["timestamps"]) if h["timestamps"] else 0
        
        # 전체 이탈 비율 10% 이상 -> -10
        if ratio >= GAZE_OFF_RATIO_LIMIT:
            scores["gaze"] -= 10
            deductions.append(f"시선 불안정 비율 높음({ratio*100:.1f}%) (-10점)")
        
        # 장기 이탈 횟수당 -5 (최대 -10)
        if long_gaze_events > 0:
            ded = min(10, long_gaze_events * 5)
            scores["gaze"] -= ded
            deductions.append(f"2초 이상 시선 이탈 {long_gaze_events}회 (-{ded}점)")

        scores["gaze"] = max(0, scores["gaze"])


        # =========================================================
        # 📝 최종 결과 집계
        # =========================================================
        final_score = sum(scores.values())
        
        summary = ""
        if final_score >= 90: summary = "매우 안정적이고 훌륭한 비언어적 태도입니다."
        elif final_score >= 70: summary = "전반적으로 양호하나 일부 개선이 필요합니다."
        else: summary = "시선 처리와 자세에서 불안정한 모습이 보입니다."

        # 피드백 문자열 생성
        feedback_str = summary
        if deductions:
            feedback_str += "\n\n[주요 감점 요인]\n- " + "\n- ".join(deductions[:3]) # 상위 3개만

        return {
            "score": int(final_score),
            "feedback": feedback_str,
            "details": {
                "head_score": scores["head"],
                "smile_score": scores["smile"],
                "blink_score": scores["blink"],
                "gaze_score": scores["gaze"],
                "rpm": round(rpm, 1),
                "timeline_timestamps": h["timestamps"][::15], # 그래프용 (데이터 줄임)
                "timeline_head": h["head_angles"][::15]
            }
        }

# 싱글톤 인스턴스
_visual_engine = VisualAnalysisEngine()

def run_visual(video_path:str) -> Dict[str, Any]:
    return _visual_engine.analyze(video_path)