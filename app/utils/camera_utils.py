import cv2
import numpy as np
import tempfile
from streamlit_webrtc import VideoTransformerBase

# OpenCV Haar Cascade 얼굴 탐지
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)

class FaceGuideTransformer(VideoTransformerBase):
    """
    실시간 웹캠 영상에 얼굴 가이드 원 표시
    얼굴이 원 안에 들어오면 초록, 아니면 빨강
    녹화 기능도 지원
    """
    def __init__(self):
        self.recorded_frames = []  # 녹화용 프레임 저장

    def recv(self, frame):
        # 프레임 변환
        img = frame.to_ndarray(format="bgr24")
        h, w, _ = img.shape

        # 화면 중앙 원 좌표
        center_x, center_y = w // 2, int(h * 0.45)
        radius = int(w * 0.18)

        # 얼굴 감지
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

            # 얼굴 위치 표시
            color = (0, 255, 0) if is_inside else (0, 0, 255)
            cv2.rectangle(img, (x, y), (x+fw, y+fh), color, 2)

        # 중앙 원 그리기
        color = (0, 255, 0) if is_inside else (0, 0, 255)
        cv2.circle(img, (center_x, center_y), radius, color, 4)

        # 상태 텍스트
        text = "위치 적절 ✅" if is_inside else "얼굴을 원 안으로 이동 🟥"
        cv2.putText(img, text, (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

        # 녹화용으로 프레임 저장
        self.recorded_frames.append(img)

        return img

    def get_recorded_video(self):
        """
        녹화된 프레임을 mp4로 저장 후 파일 경로 반환
        """
        if not self.recorded_frames:
            return None

        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
        h, w, _ = self.recorded_frames[0].shape
        out = cv2.VideoWriter(tmp_file, cv2.VideoWriter_fourcc(*'mp4v'), 30, (w, h))
        for frame in self.recorded_frames:
            out.write(frame)
        out.release()

        # 녹화 초기화
        self.recorded_frames = []
        return tmp_file
