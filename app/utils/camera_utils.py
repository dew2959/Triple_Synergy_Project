import cv2
import numpy as np
import av
from streamlit_webrtc import VideoProcessorBase

# OpenCV 얼굴 탐지 모델 로드
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)

class FaceGuideTransformer(VideoProcessorBase):
    def __init__(self):
            # 이제 프레임 리스트를 만들지 않습니다. (메모리 절약)
            pass

    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        img = frame.to_ndarray(format="bgr24")
        
        try:
            h, w, _ = img.shape
            center_x, center_y = w // 2, int(h * 0.45)
            radius = int(w * 0.18)

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 5)
            
            is_inside = False
            if len(faces) > 0:
                # 가장 큰 얼굴 선택
                x, y, fw, fh = max(faces, key=lambda f: f[2]*f[3])
                face_x = x + fw // 2
                face_y = y + fh // 2
                # 얼굴 중심이 가이드 원 안에 있는지 확인
                if np.sqrt((face_x - center_x)**2 + (face_y - center_y)**2) < radius * 0.5:
                    is_inside = True
                cv2.rectangle(img, (x, y), (x+fw, y+fh), (0, 255, 0) if is_inside else (0, 0, 255), 2)

            # 가이드 원 그리기
            color = (0, 255, 0) if is_inside else (0, 0, 255)
            cv2.circle(img, (center_x, center_y), radius, color, 4)
            status_text = "Good" if is_inside else "Move Center"
            cv2.putText(img, status_text, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        except Exception:
            pass
        
        # 처리된 이미지를 다시 프레임으로 변환하여 반환
        return av.VideoFrame.from_ndarray(img, format="bgr24")

# [중요] AudioRecorder 클래스는 더 이상 필요 없습니다. 
# MediaRecorder가 내부적으로 오디오 스트림을 가로채서 바로 저장하기 때문입니다.
