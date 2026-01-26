#----------------------
# 저장 함수들
#----------------------
# mp4 저장 

# ==============================================================================
# 오디오/비디오를 하나로 합침
# 기존 save_mp4, save_wav -> save_muxed_video
# 비디오(h264) + 오디오(aac) 스트림 동시 생성
# test 요구됨.
# (by ddu, Gemini 3 Pro)
# ==============================================================================

import av
import tempfile
import numpy as np
import streamlit as st

# FFmpeg의 로그 레벨을 상세하게 설정 (DEBUG, INFO, WARNING, ERROR 등)
# 'DEBUG'로 설정하면 프레임 하나하나 인코딩되는 과정까지 모두 볼 수 있습니다.
av.logging.set_level(av.logging.VERBOSE)

def save_muxed_video(video_frames, audio_frames):
    """
    비디오 프레임과 오디오 프레임을 하나의 MP4 파일로 저장 (Muxing)
    """
    if not video_frames:
        return None

    # 임시 파일 생성
    tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    output_path = tfile.name

    try:
        container = av.open(output_path, mode="w")

        # 1. 비디오 스트림 추가
        video_stream = container.add_stream("h264", rate=30)
        first_frame = video_frames[0]
        video_stream.width = first_frame.width
        video_stream.height = first_frame.height
        video_stream.pix_fmt = "yuv420p"
        video_stream.time_base = av.Fraction(1, fps) # 타임베이스 명시

        # 2. 오디오 스트림 추가 (오디오 프레임이 있는 경우)
        audio_stream = None
        if audio_frames:
            # 오디오 프레임의 포맷 확인 (보통 s16이나 fltp)
            try:
                audio_stream = container.add_stream("aac", rate=48000)
            except Exception as e:
                st.warning(f"오디오 스트림 생성 실패: {e}")

        # 3. 비디오 인코딩 및 Muxing
        for i, frame in enumerate(video_frames):
            frame.pts = i # 순차적으로 PTS 부여
            for packet in video_stream.encode(frame):
                container.mux(packet)
                
        # 비디오 버퍼 비우기
        for packet in video_stream.encode():
            container.mux(packet)

        # 4. 오디오 인코딩 및 Muxing
        if audio_stream:
            for i, frame in enumerate(audio_frames):
                # 오디오 프레임 pts도 비디오와 동기화가 필요하지만, 
                # 단순 저장 시에는 순차 부여가 안전함
                frame.pts = None 
                try:
                    for packet in audio_stream.encode(frame):
                        container.mux(packet)
                except:
                    continue
            for packet in audio_stream.encode():
                container.mux(packet)

        container.close()
        return output_path
    except Exception as e:
        print(f"Muxing failed: {e}")
        return None