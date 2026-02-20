from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from app.core.config import settings


def _base_url() -> str:
    return (settings.GPU_BASE_URL or "").rstrip("/")


def _is_enabled() -> bool:
    return bool(settings.GPU_REMOTE_ENABLED and _base_url())


def remote_run_stt(
    audio_path: str,
    model_name: str = "small",
    language: Optional[str] = "ko",
) -> Dict[str, Any]:
    """
    GPU 서버의 /stt 엔드포인트를 직접 호출.
    - 성공 시 v0 contract(dict) 반환을 기대.
    - 실패 시 예외를 던지며, 호출부에서 로컬 fallback 처리.
    """
    if not _is_enabled():
        raise RuntimeError("GPU remote STT is not enabled")

    url = f"{_base_url()}/stt"

    with open(audio_path, "rb") as f:
        files = {
            "audio": ("audio.wav", f, "audio/wav"),
        }
        data = {
            "model_name": model_name,
            "language": language or "",
        }
        response = requests.post(
            url,
            files=files,
            data=data,
            timeout=settings.GPU_TIMEOUT_SEC,
        )

    response.raise_for_status()
    payload = response.json()

    if not isinstance(payload, dict):
        raise ValueError("Invalid STT response payload")
    return payload


def remote_generate_lipsync(
    audio_bytes: bytes,
    filename: str,
    avatar_url: str,
    resize_factor: int = 1,
    nosmooth: bool = False,
) -> bytes:
    """
    GPU 서버의 /lipsync 엔드포인트를 직접 호출해 mp4 bytes를 반환.
    실패 시 예외를 던지며, 호출부에서 로컬 fallback 처리.
    """
    if not _is_enabled():
        raise RuntimeError("GPU remote lipsync is not enabled")

    url = f"{_base_url()}/lipsync"

    files = {
        "audio": (filename or "audio.mp3", audio_bytes, "audio/mpeg"),
    }
    data = {
        "avatar_url": avatar_url,
        "resize_factor": str(resize_factor),
        "nosmooth": "true" if nosmooth else "false",
    }

    response = requests.post(
        url,
        files=files,
        data=data,
        timeout=settings.GPU_TIMEOUT_SEC,
    )
    if response.status_code >= 400:
        detail = (response.text or "").strip()
        raise RuntimeError(f"GPU /lipsync failed: status={response.status_code}, detail={detail}")
    return response.content
