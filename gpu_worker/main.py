from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import requests
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from app.engines.stt.engine import run_stt
from app.core.config import settings

app = FastAPI(title="Triple Synergy GPU Worker", version="0.1.0")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WAV2LIP_DIR = PROJECT_ROOT / "third_party" / "Wav2Lip"
WAV2LIP_CKPT = WAV2LIP_DIR / "checkpoints" / "wav2lip_gan.pth"


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/health/gpu")
def health_gpu() -> dict:
    try:
        import torch

        cuda_available = bool(torch.cuda.is_available())
        device_count = int(torch.cuda.device_count()) if cuda_available else 0
        device_name = torch.cuda.get_device_name(0) if cuda_available and device_count > 0 else None

        nvidia_smi_ok = False
        nvidia_smi_out = ""
        try:
            proc = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            nvidia_smi_ok = proc.returncode == 0
            nvidia_smi_out = (proc.stdout or proc.stderr or "").strip()
        except Exception as e:
            nvidia_smi_out = str(e)

        return {
            "status": "ok",
            "torch_cuda_available": cuda_available,
            "torch_device_count": device_count,
            "torch_device_name": device_name,
            "nvidia_smi_ok": nvidia_smi_ok,
            "nvidia_smi": nvidia_smi_out,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
        }


@app.post("/stt")
async def stt(
    audio: UploadFile = File(...),
    model_name: str = Form("small"),
    language: str = Form("ko"),
):
    tmp_dir = tempfile.mkdtemp(prefix="gpu_stt_")
    audio_path = os.path.join(tmp_dir, audio.filename or "audio.wav")
    try:
        audio_bytes = await audio.read()
        with open(audio_path, "wb") as f:
            f.write(audio_bytes)

        original_remote_enabled = settings.GPU_REMOTE_ENABLED
        settings.GPU_REMOTE_ENABLED = False
        try:
            out = run_stt(audio_path=audio_path, model_name=model_name, language=language or None)
        finally:
            settings.GPU_REMOTE_ENABLED = original_remote_enabled
        return out
    finally:
        try:
            shutil.rmtree(tmp_dir)
        except Exception:
            pass


@app.post("/lipsync")
async def lipsync(
    audio: UploadFile = File(...),
    avatar_url: str = Form(...),
    resize_factor: int = Form(1),
    nosmooth: bool = Form(False),
):
    if not WAV2LIP_DIR.exists():
        raise HTTPException(status_code=500, detail=f"WAV2LIP_DIR not found: {WAV2LIP_DIR}")
    if not WAV2LIP_CKPT.exists():
        raise HTTPException(status_code=500, detail=f"WAV2LIP_CHECKPOINT not found: {WAV2LIP_CKPT}")

    tmp_dir = tempfile.mkdtemp(prefix="gpu_wav2lip_")
    try:
        face_path = os.path.join(tmp_dir, "face.jpg")
        audio_in_path = os.path.join(tmp_dir, "audio_input")
        audio_wav_path = os.path.join(tmp_dir, "audio.wav")
        out_mp4_path = os.path.join(tmp_dir, "result.mp4")

        img_res = requests.get(avatar_url, timeout=15)
        if img_res.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Failed to fetch avatar_url: {img_res.status_code}")
        with open(face_path, "wb") as f:
            f.write(img_res.content)

        audio_bytes = await audio.read()
        with open(audio_in_path, "wb") as f:
            f.write(audio_bytes)

        cmd_ffmpeg = ["ffmpeg", "-y", "-i", audio_in_path, "-ac", "1", "-ar", "16000", audio_wav_path]
        ffmpeg_proc = subprocess.run(cmd_ffmpeg, capture_output=True, text=True)
        if ffmpeg_proc.returncode != 0 or not os.path.exists(audio_wav_path):
            raise HTTPException(status_code=500, detail="ffmpeg failed before wav2lip inference")

        cmd_w2l = [
            sys.executable,
            "inference.py",
            "--checkpoint_path",
            str(WAV2LIP_CKPT),
            "--face",
            face_path,
            "--audio",
            audio_wav_path,
            "--outfile",
            out_mp4_path,
            "--resize_factor",
            str(resize_factor),
            "--static",
            "1",
            "--wav2lip_batch_size",
            "128",
            "--face_det_batch_size",
            "1",
            "--fps",
            "15",
        ]
        if nosmooth:
            cmd_w2l.append("--nosmooth")

        w2l_proc = subprocess.run(cmd_w2l, cwd=str(WAV2LIP_DIR), capture_output=True, text=True)
        if w2l_proc.returncode != 0 or not os.path.exists(out_mp4_path):
            raise HTTPException(status_code=500, detail="wav2lip inference failed")

        with open(out_mp4_path, "rb") as f:
            mp4_bytes = f.read()
        return Response(content=mp4_bytes, media_type="video/mp4")
    finally:
        try:
            shutil.rmtree(tmp_dir)
        except Exception:
            pass
