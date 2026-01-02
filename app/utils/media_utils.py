# app/utils/media_utils.py
import os
from moviepy.editor import VideoFileClip

class MediaUtils:
    @staticmethod
    def extract_audio(video_path: str) -> str:
        """
        영상 파일(.mp4)에서 오디오(.wav)를 추출하여 같은 폴더에 저장합니다.
        반환값: 생성된 오디오 파일의 절대 경로
        """
        try:
            # 1. 오디오 파일명 생성 (video.mp4 -> video.wav)
            # os.path.splitext("uploads/1_test.mp4") -> ("uploads/1_test", ".mp4")
            base_name, _ = os.path.splitext(video_path)
            audio_path = f"{base_name}.wav"

            # 2. 이미 변환된 파일이 있는지 확인 (중복 방지)
            if os.path.exists(audio_path):
                print(f"🔊 [MediaUtils] 오디오 파일이 이미 존재합니다: {audio_path}")
                return audio_path

            print(f"🔊 [MediaUtils] 오디오 추출 시작: {video_path} -> {audio_path}")

            # 3. MoviePy로 변환 수행
            video = VideoFileClip(video_path)
            # logger=None: 불필요한 로그 출력 끄기
            video.audio.write_audiofile(audio_path, codec='pcm_s16le', logger=None) 
            video.close()
            
            print(f"✅ [MediaUtils] 오디오 추출 완료")
            return audio_path

        except Exception as e:
            print(f"❌ [MediaUtils] 오디오 추출 실패: {e}")
            raise e