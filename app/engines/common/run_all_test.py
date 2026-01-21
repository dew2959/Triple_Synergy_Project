from __future__ import annotations

import json
import argparse

from app.engines.common.contract_v0 import assert_v0_contract

from app.engines.visual.engine import run_visual
from app.engines.stt.engine import run_stt
from app.engines.voice.engine import run_voice
from app.engines.llm.engine import run_content


import time
from datetime import datetime, timezone

def timed(module_name, fn, *args, **kwargs):
    t0 = time.perf_counter()
    started_at = datetime.now(timezone.utc).isoformat()
    try:
        out = fn(*args, **kwargs)
        return out
    finally:
        ended_at = datetime.now(timezone.utc).isoformat()
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
        print(f"[timing] {module_name} elapsed_ms={elapsed_ms} start={started_at} end={ended_at}", flush=True)



def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=str, default=None, help="mp4 path (for visual)")
    parser.add_argument("--audio", type=str, required=True, help="wav path (for stt/voice)")
    parser.add_argument("--question", type=str, default="", help="question text (for content)")
    args = parser.parse_args()

    video_path = args.video
    audio_path = args.audio
    question_text = args.question or ""

    # 1) VISUAL (optional)
    if video_path:
        visual_out = timed("visual", run_visual, video_path)
        assert_v0_contract(visual_out, expected_module="visual")
        print("=== VISUAL ===")
        print(json.dumps(visual_out, ensure_ascii=False, indent=2))


    # 2) STT
    stt_out = timed("stt", run_stt, audio_path)
    assert_v0_contract(stt_out, expected_module="stt")
    stt_metrics = stt_out.get("metrics", {})
    stt_text = stt_metrics.get("text")
    stt_segments = stt_metrics.get("segments")

    print("=== STT ===")
    print(json.dumps(stt_out, ensure_ascii=False, indent=2))

    # 3) VOICE (wpm 채우려면 stt_text/segments 전달)
    voice_out = timed("voice", run_voice, audio_path, stt_text=stt_text, stt_segments=stt_segments)
    assert_v0_contract(voice_out, expected_module="voice")

    print("=== VOICE ===")
    print(json.dumps(voice_out, ensure_ascii=False, indent=2))

    # 4) CONTENT (stt_text 없으면 스킵)
    if stt_text:
        content_out = timed("content", run_content, stt_text, question_text=question_text)
        assert_v0_contract(content_out, expected_module="content")
        print("=== CONTENT ===")
        print(json.dumps(content_out, ensure_ascii=False, indent=2))

    else:
        print("=== CONTENT ===")
        print("Skipped: stt_text is empty or None")


if __name__ == "__main__":
    main()
