#----------------------
# 저장 함수들
#----------------------
# mp4 저장 
import av
import tempfile

def save_mp4(video_frames):
    if not video_frames:
        return None

    tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    output = tfile.name
    tfile.close()

    container = av.open(output, mode="w")
    stream = container.add_stream("h264", rate=30)

    stream.width = video_frames[0].width
    stream.height = video_frames[0].height
    stream.pix_fmt = "yuv420p"

    for frame in video_frames:
        frame.pts = None
        for packet in stream.encode(frame):
            container.mux(packet)

    for packet in stream.encode():
        container.mux(packet)

    container.close()
    return output

#  wav 저장
import wave
import numpy as np

def save_wav(audio_frames):
    if not audio_frames:
        return None

    tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    output = tfile.name
    tfile.close()

    pcm = []
    for f in audio_frames:
        pcm.append(f.to_ndarray())

    pcm = np.concatenate(pcm, axis=1)

    with wave.open(output, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)      # 16bit
        wf.setframerate(48000)
        wf.writeframes(pcm.tobytes())

    return output
