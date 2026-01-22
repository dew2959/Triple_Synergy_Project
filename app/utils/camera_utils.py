import cv2
import numpy as np
import tempfile
import av  # [중요] av 라이브러리 필요 (pip install av)
from streamlit_webrtc import VideoProcessorBase # VideoTransformerBase 대신 최신 Base 사용 권장

# OpenCV Haar Cascade 얼굴 탐지 (경로는 환경에 맞게 유지)
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)

class FaceGuideTransformer(VideoProcessorBase):
    """
    실시간 웹캠 영상에 얼굴 가이드 원 표시 및 녹화 제어
    """
    def __init__(self):
        self.recording = False      # [수정] 녹화 상태 제어 플래그 추가
        self.recorded_frames = []   # 녹화 데이터 저장소

    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        # 1. av.VideoFrame -> NumPy 배열 변환
        img = frame.to_ndarray(format="bgr24")
        
        # ---------------------------------------------------------
        # 영상 처리 로직 (기존과 동일하되 예외처리 추가)
        # ---------------------------------------------------------
        h, w, _ = img.shape
        center_x, center_y = w // 2, int(h * 0.45)
        radius = int(w * 0.18)

        # 얼굴 감지 (성능을 위해 try-except 감싸기)
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
            
            is_inside = False

            if len(faces) > 0:
                # 가장 큰 얼굴 하나만 사용
                x, y, fw, fh = max(faces, key=lambda f: f[2]*f[3])
                face_x = x + fw // 2
                face_y = y + fh // 2

                distance = np.sqrt((face_x - center_x) ** 2 + (face_y - center_y) ** 2)
                if distance < radius * 0.5:
                    is_inside = True

                # 얼굴 박스 그리기
                color = (0, 255, 0) if is_inside else (0, 0, 255)
                cv2.rectangle(img, (x, y), (x+fw, y+fh), color, 2)

            # 중앙 원 및 텍스트 그리기
            circle_color = (0, 255, 0) if is_inside else (0, 0, 255)
            cv2.circle(img, (center_x, center_y), radius, circle_color, 4)
            
            # 한글 텍스트는 cv2.putText로 깨질 수 있으므로 영문 권장 (또는 PIL 사용)
            status_text = "Good Position" if is_inside else "Move to Circle"
            cv2.putText(img, status_text, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, circle_color, 2)
            
        except Exception as e:
            print(f"Image Processing Error: {e}")

        # ---------------------------------------------------------
        # [중요 수정] 녹화 플래그가 True일 때만 저장
        # ---------------------------------------------------------
        if self.recording:
            self.recorded_frames.append(img)

        # [중요 수정] NumPy 배열 -> av.VideoFrame 변환 후 반환
        return av.VideoFrame.from_ndarray(img, format="bgr24")

    def get_recorded_video(self):
        """녹화된 프레임을 mp4로 저장 후 파일 경로 반환"""
        if not self.recorded_frames:
            return None

        try:
            # 임시 파일 생성
            tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            tmp_file_path = tfile.name
            tfile.close() # 윈도우 호환성을 위해 닫기

            h, w, _ = self.recorded_frames[0].shape
            
            # 코덱 설정 (mp4v 또는 avc1)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(tmp_file_path, fourcc, 20.0, (w, h)) # 20~30 fps 조절

            for frame in self.recorded_frames:
                out.write(frame)
            out.release()

            # 녹화 데이터 초기화 (메모리 해제)
            self.recorded_frames = []
            return tmp_file_path
            
        except Exception as e:
            print(f"Video Save Error: {e}")
            return None