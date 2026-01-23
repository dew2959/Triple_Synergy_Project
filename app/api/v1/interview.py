import shutil
import os
from fastapi import APIRouter, UploadFile, File, Depends, Form, BackgroundTasks, HTTPException
from psycopg2.extensions import connection 

from app.api.deps import get_db_conn
from app.schemas.interview import AnswerResponse, RetryAnalysisResponse
from app.repositories.answer_repo import answer_repo
from app.services.analysis_service import analysis_service
from app.core.db import get_db_connection
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

# ==============================
# 업로드 경로 설정
# ==============================
UPLOAD_DIR = getattr(settings, "UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# =========================================================
#  백그라운드 분석 실행
# =========================================================
def run_background_analysis(answer_id: int, file_path: str):
    """
    백그라운드 작업: 요청(Request)과 독립적으로 실행됨.
    따라서 Depends로 받은 conn을 쓰면 안 되고(이미 닫힘),
    여기서 스스로 연결을 맺고 끊어야 합니다.
    """
    with get_db_connection() as conn:
        analysis_service.run_full_analysis(conn, answer_id, file_path)


# =========================================================
#  API Endpoints
# =========================================================

@router.post("/upload", response_model=AnswerResponse)
def upload_interview_video(
    background_tasks: BackgroundTasks,
    question_id: int = Form(...),
    file: UploadFile = File(...),
    conn: connection = Depends(get_db_conn)
):
    """
    [면접 영상 업로드]
    """
    
    # 1. 물리적 파일 저장
    safe_filename = f"{question_id}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # 2. DB에 메타데이터 저장
    new_answer = answer_repo.create(
        conn=conn, 
        question_id=question_id, 
        video_path=file_path
    )
    conn.commit()

    # 3. 백그라운드 분석 작업 등록
    background_tasks.add_task(
        run_background_analysis, 
        new_answer['answer_id'],
        file_path
    )
    
    # 4. 결과 반환
    return new_answer

# ==============================
# 재분석 요청 (관리자/디버깅용)
# ==============================
@router.post("/{answer_id}/analyze", response_model=RetryAnalysisResponse)
def retry_analysis(
    answer_id: int,
    background_tasks: BackgroundTasks,
    conn: connection = Depends(get_db_conn)
):
    """
    기존 답변 재분석 요청
    """
    # 1. 답변 존재 확인
    answer = answer_repo.get_by_id(conn, answer_id)
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")
    
    # 2. 영상 파일 존재 확인
    # (answer는 딕셔너리이므로 ['video_path']로 접근)
    if not os.path.exists(answer['video_path']):
        raise HTTPException(status_code=400, detail="Video file is missing on server")

    # 3. 백그라운드 작업 다시 등록
    background_tasks.add_task(
        run_background_analysis, 
        answer['answer_id'], 
        answer['video_path']
    )
    
    return RetryAnalysisResponse(message=f"Re-analysis started for answer {answer_id}")


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
            "--resize_factor", str(resize_factor),
            "--static", "1" # ✅ 추가
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
            "-vf", "scale=iw*2 :ih*2:flags=lanczos,unsharp=5:5:1.2:5:5:0.0",
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
