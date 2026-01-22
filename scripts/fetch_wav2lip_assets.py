from __future__ import annotations
import subprocess
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]     # project root
THIRD_PARTY = ROOT / "third_party"
WAV2LIP_DIR = THIRD_PARTY / "Wav2Lip"

WAV2LIP_REPO = "https://github.com/Rudrabha/Wav2Lip.git"
S3FD_URL = "https://www.adrianbulat.com/downloads/python-fan/s3fd-619a316812.pth"
CKPT_URL = "https://github.com/GucciFlipFlops1917/wav2lip-hq-updated-ESRGAN/releases/download/v0.0.1/wav2lip_gan.pth"

S3FD_DST = WAV2LIP_DIR / "face_detection" / "detection" / "sfd" / "s3fd.pth"
CKPT_DST = WAV2LIP_DIR / "checkpoints" / "wav2lip_gan.pth"

def run(cmd: list[str], cwd: Path | None = None):
    print(">", " ".join(cmd))
    subprocess.check_call(cmd, cwd=str(cwd) if cwd else None)

def ensure_repo():
    THIRD_PARTY.mkdir(parents=True, exist_ok=True)
    if WAV2LIP_DIR.exists() and (WAV2LIP_DIR / "inference.py").exists():
        print(f"[OK] Wav2Lip repo exists: {WAV2LIP_DIR}")
        return
    print("[..] Cloning Wav2Lip repo...")
    run(["git", "clone", WAV2LIP_REPO, str(WAV2LIP_DIR)])

def download(url: str, dst: Path, min_mb: int):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and dst.stat().st_size > min_mb * 1024 * 1024:
        print(f"[OK] exists: {dst} ({dst.stat().st_size/1024/1024:.1f} MB)")
        return

    print(f"[..] Download: {url}\n     -> {dst}")
    with requests.get(url, stream=True, timeout=120, allow_redirects=True) as r:
        r.raise_for_status()
        tmp = dst.with_suffix(dst.suffix + ".tmp")
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
        tmp.replace(dst)

    size_mb = dst.stat().st_size / 1024 / 1024
    if size_mb < min_mb:
        raise RuntimeError(f"Downloaded file too small ({size_mb:.1f} MB). URL blocked or failed.")
    print(f"[OK] downloaded: {dst} ({size_mb:.1f} MB)")

def main():
    ensure_repo()
    download(S3FD_URL, S3FD_DST, min_mb=50)   # s3fd ~86MB
    download(CKPT_URL, CKPT_DST, min_mb=200)  # wav2lip_gan 수백MB
    print("[OK] All assets present.")
    print("WAV2LIP_DIR =", WAV2LIP_DIR)
    print("S3FD_DST   =", S3FD_DST)
    print("CKPT_DST   =", CKPT_DST)

if __name__ == "__main__":
    main()
