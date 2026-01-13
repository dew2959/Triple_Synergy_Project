# app/utils/media_utils.py
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional


class MediaToolError(RuntimeError):
    pass


class MediaUtils:
    @staticmethod
    def _ensure_ffmpeg() -> None:
        if shutil.which("ffmpeg") is None:
            raise MediaToolError("ffmpeg가 설치되어 있지 않습니다. (PATH에 ffmpeg 필요)")

    @staticmethod
    def compress_video(
        video_path: str,
        output_path: Optional[str] = None,
        *,
        max_width: int = 1280,
        max_height: int = 720,
        fps: Optional[int] = None,
        crf: int = 28,
        preset: str = "veryfast",
        audio_bitrate: str = "96k",
        overwrite: bool = False,
    ) -> str:
        """
        전체 영상 용량 줄이기 (리사이즈 + fps 제한 + H.264 재인코딩)
        - 비율 유지 + 짝수 해상도 보정 포함
        """
        MediaUtils._ensure_ffmpeg()

        in_path = Path(video_path)
        if not in_path.exists():
            raise FileNotFoundError(f"video not found: {video_path}")

        if output_path is None:
            output_path = str(in_path.with_suffix(".compressed.mp4"))
        out_path = Path(output_path)

        if out_path.exists() and not overwrite:
            return str(out_path.resolve())

        vf = (
            f"scale=w={max_width}:h={max_height}:force_original_aspect_ratio=decrease,"
            f"pad=ceil(iw/2)*2:ceil(ih/2)*2,"
            f"setsar=1"
        )

        cmd = [
            "ffmpeg",
            "-y" if overwrite else "-n",
            "-i", str(in_path),
            "-vf", vf,
            "-c:v", "libx264",
            "-preset", preset,
            "-crf", str(crf),
            "-movflags", "+faststart",
            "-c:a", "aac",
            "-b:a", audio_bitrate,
        ]

        if fps is not None:
            cmd += ["-r", str(fps)]

        cmd += [str(out_path)]

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            raise MediaToolError(f"ffmpeg compress 실패\nSTDERR:\n{e.stderr[-2000:]}") from e

        return str(out_path.resolve())


    @staticmethod
    def extract_audio(video_path: str, output_path: Optional[str] = None, *, overwrite: bool = False) -> str:
        """
        mp4 -> wav 추출
        - 기존 MoviePy 대신 ffmpeg로 (빠르고 단순)
        """
        MediaUtils._ensure_ffmpeg()

        in_path = Path(video_path)
        if not in_path.exists():
            raise FileNotFoundError(f"video not found: {video_path}")

        if output_path is None:
            base, _ = os.path.splitext(video_path)
            output_path = f"{base}.wav"
        out_path = Path(output_path)

        if out_path.exists() and not overwrite:
            return str(out_path.resolve())

        cmd = [
            "ffmpeg",
            "-y" if overwrite else "-n",
            "-i", str(in_path),
            "-vn",  # video stream 제거
            "-acodec", "pcm_s16le",
            "-ar", "16000",  # 음성 분석/whisper에 자주 쓰는 샘플레이트
            "-ac", "1",      # mono
            str(out_path),
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            raise MediaToolError(f"ffmpeg audio 추출 실패\nSTDERR:\n{e.stderr[-2000:]}") from e

        return str(out_path.resolve())
