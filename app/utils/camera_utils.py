import cv2
import numpy as np
import av
from streamlit_webrtc import VideoProcessorBase

# OpenCV 얼굴 탐지 모델 로드
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)

class FaceGuideTransformer(VideoProcessorBase):
    # -------------------------------------------------------
    # 1. 비디오 처리 (기존 로직 유지 + 프레임 저장)
    # -------------------------------------------------------
    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        img = frame.to_ndarray(format="bgr24")
        
        # --- 얼굴 가이드 그리기 로직 (기존과 동일) ---
        h, w, _ = img.shape
        center_x, center_y = w // 2, int(h * 0.45)
        radius = int(w * 0.18)

        try:
            # 가벼운 처리를 위해 격주로 감지하거나 try-except
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 5)
            
            is_inside = False
            if len(faces) > 0:
                x, y, fw, fh = max(faces, key=lambda f: f[2]*f[3])
                face_x = x + fw // 2
                face_y = y + fh // 2
                if np.sqrt((face_x - center_x)**2 + (face_y - center_y)**2) < radius * 0.5:
                    is_inside = True
                cv2.rectangle(img, (x, y), (x+fw, y+fh), (0, 255, 0) if is_inside else (0, 0, 255), 2)

            color = (0, 255, 0) if is_inside else (0, 0, 255)
            cv2.circle(img, (center_x, center_y), radius, color, 4)
            # 한글 깨짐 방지를 위해 영문 사용
            status_text = "Good" if is_inside else "Move Center"
            cv2.putText(img, status_text, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

        except Exception:
            pass
        
        return av.VideoFrame.from_ndarray(img, format="bgr24")

