from pathlib import Path
from app.utils.media_utils import MediaUtils

VIDEO = r"C:\Users\user\Downloads\5.failed_experience_sejin(chest)_C.mp4" 

def main():
    in_path = Path(VIDEO)
    print("Input exists:", in_path.exists(), in_path)

    compressed = MediaUtils.compress_video(
        str(in_path),
        max_width=1280,
        max_height=720,
        fps=None,
        crf=28,
        preset="veryfast",
        overwrite=True,
    )
    print("Compressed:", compressed, "size(bytes):", Path(compressed).stat().st_size)

    wav = MediaUtils.extract_audio(compressed, overwrite=True)
    print("Wav:", wav, "size(bytes):", Path(wav).stat().st_size)

if __name__ == "__main__":
    main()
