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
            # 영상 데이터가 아예 없으면 실패 처리
            if not self.video_frames:
                print("녹화 실패: 수집된 비디오 프레임이 없습니다.")
                return None

            tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            output_path = tfile.name
            tfile.close()

            try:
                container = av.open(output_path, mode="w")

                # 1. 비디오 스트림 생성
                stream_v = container.add_stream("h264", rate=30)
                stream_v.pix_fmt = "yuv420p"
                stream_v.width = self.video_frames[0].width
                stream_v.height = self.video_frames[0].height

                # 2. 오디오 스트림 생성 (있을 때만!)
                stream_a = None
                if self.audio_frames:
                    stream_a = container.add_stream("aac", layout="stereo")

                # --- [A] 비디오 저장 ---
                for frame in self.video_frames:
                    frame.pts = None
                    for packet in stream_v.encode(frame):
                        container.mux(packet)
                # 비디오 버퍼 비우기 (필수)
                for packet in stream_v.encode():
                    container.mux(packet)

                # --- [B] 오디오 저장 (조건부) ---
                # ★★★ 여기서부터 들여쓰기 주의! ★★★
                if stream_a and self.audio_frames:
                    for frame in self.audio_frames:
                        frame.pts = None
                        for packet in stream_a.encode(frame):
                            container.mux(packet)
                    
                    # [중요] 이 부분이 반드시 if문 '안쪽'에 있어야 합니다.
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