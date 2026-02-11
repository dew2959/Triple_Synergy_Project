import shutil
import os
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.core.config import settings

from fastapi.responses import Response
from openai import OpenAI
from app.schemas.interview import TTSRequest

import sys
import tempfile
import subprocess
import requests
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]  # app/api/v1/interview.py 기준: project root
WAV2LIP_DIR = PROJECT_ROOT / "third_party" / "Wav2Lip"
WAV2LIP_CKPT = WAV2LIP_DIR / "checkpoints" / "wav2lip_gan.pth"



router = APIRouter()

@router.post("/tts", summary="텍스트를 음성으로 변환")
def generate_tts(request: TTSRequest):
    """
    OpenAI TTS API를 사용하여 텍스트를 오디오(MP3) 바이너리로 반환
    """
    if not settings.OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API Key missing")
    
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    try:
        response = client.audio.speech.create(
            model="tts-1",       # tts-1: 빠름, tts-1-hd: 고품질
            voice=request.voice, # 면접관 목소리 선택
            input=request.text
        )
        
        # 바이너리 데이터를 그대로 반환 (audio/mpeg)
        return Response(content=response.content, media_type="audio/mpeg")
        
    except Exception as e:
        print(f"TTS Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    


@router.post("/lipsync", summary="오디오 + 아바타 이미지(URL)로 립싱크 mp4 생성")
async def generate_lipsync(
    audio: UploadFile = File(...),
    avatar_url: str = Form(...),
    resize_factor: int = Form(1),
    nosmooth: bool = Form(False),
):
    """
    - audio: mp3/wav 오디오 파일 (Streamlit에서 TTS 결과 bytes 업로드)
    - avatar_url: 면접관 이미지 URL (Streamlit에서 쓰는 URL 그대로)
    - 반환: video/mp4 바이너리
    """
    if not WAV2LIP_DIR.exists():
        raise HTTPException(status_code=500, detail=f"WAV2LIP_DIR not found: {WAV2LIP_DIR}")
    if not WAV2LIP_CKPT.exists():
        raise HTTPException(status_code=500, detail=f"WAV2LIP_CHECKPOINT not found: {WAV2LIP_CKPT}")

    tmp_dir = tempfile.mkdtemp(prefix="wav2lip_")

    err_path = os.path.join(tmp_dir, "wav2lip_stderr.txt")
    out_path = os.path.join(tmp_dir, "wav2lip_stdout.txt")

    try:
        face_path = os.path.join(tmp_dir, "face.jpg")
        audio_in_path = os.path.join(tmp_dir, "audio_input")
        audio_wav_path = os.path.join(tmp_dir, "audio.wav")
        out_mp4_path = os.path.join(tmp_dir, "result.mp4")

        # 2) avatar_url 이미지 다운로드
        try:
            img_res = requests.get(avatar_url, timeout=15)
            if img_res.status_code != 200:
                raise HTTPException(status_code=400, detail=f"Failed to fetch avatar_url: {img_res.status_code}")
            with open(face_path, "wb") as f:
                f.write(img_res.content)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"avatar_url download error: {e}")

        # 3) 오디오 저장
        audio_bytes = await audio.read()
        with open(audio_in_path, "wb") as f:
            f.write(audio_bytes)

        # 4) ffmpeg로 16k mono wav 변환
        cmd_ffmpeg = ["ffmpeg", "-y", "-i", audio_in_path, "-ac", "1", "-ar", "16000", audio_wav_path]
        r1 = subprocess.run(cmd_ffmpeg, capture_output=True, text=True)

        with open(os.path.join(tmp_dir, "ffmpeg_stderr.txt"), "w", encoding="utf-8") as f:
            f.write(r1.stderr or "")
        with open(os.path.join(tmp_dir, "ffmpeg_stdout.txt"), "w", encoding="utf-8") as f:
            f.write(r1.stdout or "")

        if r1.returncode != 0 or not os.path.exists(audio_wav_path):
            raise HTTPException(status_code=500, detail=f"ffmpeg failed. See logs in: {tmp_dir}")

        # 5) wav2lip 실행
        cmd_w2l = [
            sys.executable, "inference.py",
            "--checkpoint_path", str(WAV2LIP_CKPT),
            "--face", face_path,
            "--audio", audio_wav_path,
            "--outfile", out_mp4_path,
            "--resize_factor", "4", # GPU로 올렸을 때 수정할 부분 1
            "--static", "1", # ✅ 추가
            "--wav2lip_batch_size", "128", # 시간 줄이기 위해 추가 1
            "--face_det_batch_size", "1", # 시간 줄이기 위해 추가 2
            "--fps", "15", # 시간 줄이기 위해 추가 3
        ]
        if nosmooth:
            cmd_w2l.append("--nosmooth")

        r2 = subprocess.run(cmd_w2l, cwd=str(WAV2LIP_DIR), capture_output=True, text=True)

        with open(err_path, "w", encoding="utf-8") as f:
            f.write(r2.stderr or "")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(r2.stdout or "")

        if r2.returncode != 0 or not os.path.exists(out_mp4_path):
            raise HTTPException(status_code=500, detail=f"wav2lip inference failed. See logs in: {tmp_dir}")

        # ✅ 6) (추가) 결과 mp4 화질 개선 후처리: 업스케일 + 샤픈
        enhanced_mp4_path = os.path.join(tmp_dir, "result_enhanced.mp4")
        cmd_enhance = [
            "ffmpeg", "-y",
            "-i", out_mp4_path,
            # "-vf", "scale=iw*2 :ih*2:flags=lanczos,unsharp=5:5:1.2:5:5:0.0", # GPU로 올렸을 때 주석 풀 부분 2
            "-c:v", "libx264",
            "-crf", "18",
            "-preset", "veryfast",
            "-c:a", "copy",
            enhanced_mp4_path
        ]
        r3 = subprocess.run(cmd_enhance, capture_output=True, text=True)

        # 후처리 로그 저장(디버그용)
        with open(os.path.join(tmp_dir, "enhance_stderr.txt"), "w", encoding="utf-8") as f:
            f.write(r3.stderr or "")
        with open(os.path.join(tmp_dir, "enhance_stdout.txt"), "w", encoding="utf-8") as f:
            f.write(r3.stdout or "")

        final_mp4_path = enhanced_mp4_path if (r3.returncode == 0 and os.path.exists(enhanced_mp4_path)) else out_mp4_path

        # 7) mp4 반환
        with open(final_mp4_path, "rb") as f:
            mp4_bytes = f.read()
        return Response(content=mp4_bytes, media_type="video/mp4")

    finally:
        # 디버깅 끝나면 아래 주석 풀어서 temp 폴더 정리해도 됨
        # try:
        #     shutil.rmtree(tmp_dir)
        # except:
        #     pass
        pass
