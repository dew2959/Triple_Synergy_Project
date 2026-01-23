import cv2
import numpy as np
import tempfile
import av
import os
from streamlit_webrtc import VideoProcessorBase

# OpenCV 얼굴 탐지 모델 로드
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)

class FaceGuideTransformer(VideoProcessorBase):
    def __init__(self):
        self.recording = False
        self.video_frames = []  # 비디오 프레임 저장소
        self.audio_frames = []  # [추가] 오디오 프레임 저장소

    # -------------------------------------------------------
    # 1. 비디오 처리 (기존 로직 유지 + 프레임 저장)
    # -------------------------------------------------------
    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        img = frame.to_ndarray(format="bgr24")
        
        # --- 얼굴 인식 및 가이드 그리기 로직 (기존과 동일) ---
        h, w, _ = img.shape
        center_x, center_y = w // 2, int(h * 0.45)
        radius = int(w * 0.18)

        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 5)
            
            is_inside = False
            if len(faces) > 0:
                x, y, fw, fh = max(faces, key=lambda f: f[2]*f[3])
                face_x = x + fw // 2
                face_y = y + fh // 2
                if np.sqrt((face_x - center_x)**2 + (face_y - center_y)**2) < radius * 0.5:
                    is_inside = True
                
                color = (0, 255, 0) if is_inside else (0, 0, 255)
                cv2.rectangle(img, (x, y), (x+fw, y+fh), color, 2)

            color = (0, 255, 0) if is_inside else (0, 0, 255)
            cv2.circle(img, (center_x, center_y), radius, color, 4)
            # 한글 깨짐 방지를 위해 영문 사용
            status_text = "Good" if is_inside else "Move Center"
            cv2.putText(img, status_text, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

        except Exception:
            pass
        # -------------------------------------------------------

        # [녹화] 처리된 이미지를 비디오 프레임으로 변환하여 저장
        if self.recording:
            # 나중에 저장할 때를 위해 av.VideoFrame으로 다시 변환해서 리스트에 보관
            new_frame = av.VideoFrame.from_ndarray(img, format="bgr24")
            # 타임스탬프 유지를 위해 기존 frame의 속성 복사 (중요)
            new_frame.pts = frame.pts
            new_frame.time_base = frame.time_base
            self.video_frames.append(new_frame)

        return av.VideoFrame.from_ndarray(img, format="bgr24")

    # -------------------------------------------------------
    # 2. [추가] 오디오 처리 (이게 없으면 소리 녹음 안 됨)
    # -------------------------------------------------------
    def recv_audio(self, frame: av.AudioFrame) -> av.AudioFrame:
        if self.recording:
            self.audio_frames.append(frame)
        return frame

    # -------------------------------------------------------
    # 3. [수정] 저장 로직 (av 라이브러리로 영상+음성 합치기)
    # -------------------------------------------------------
    def get_recorded_video(self):
        if not self.video_frames or not self.audio_frames:
            return None

        # 임시 파일 경로 생성
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        output_path = tfile.name
        tfile.close()

        try:
            # PyAV 컨테이너 열기 (쓰기 모드)
            container = av.open(output_path, mode="w")

            # --- 비디오 스트림 생성 ---
            # fps는 대략 30으로 설정 (웹캠에 따라 다를 수 있음)
            stream_v = container.add_stream("h264", rate=30)
            stream_v.pix_fmt = "yuv420p"  # 웹/모바일 호환성 필수 픽셀 포맷
            stream_v.width = self.video_frames[0].width
            stream_v.height = self.video_frames[0].height

            # --- 오디오 스트림 생성 ---
            stream_a = container.add_stream("aac", layout="stereo")
            
            # 1. 비디오 패킷 인코딩 및 저장
            for frame in self.video_frames:
                frame.pts = None # pts 재설정
                for packet in stream_v.encode(frame):
                    container.mux(packet)
            # 버퍼 비우기
            for packet in stream_v.encode():
                container.mux(packet)

            # 2. 오디오 패킷 인코딩 및 저장
            for frame in self.audio_frames:
                frame.pts = None # pts 재설정
                for packet in stream_a.encode(frame):
                    container.mux(packet)
            # 버퍼 비우기
            for packet in stream_a.encode():
                container.mux(packet)

            container.close()
            
            # 메모리 초기화
            self.video_frames = []
            self.audio_frames = []
            
            return output_path

        except Exception as e:
            print(f"Muxing Error: {e}")
            return None