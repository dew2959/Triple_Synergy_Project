from __future__ import annotations

import json
import argparse
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.engines.common.contract_v0 import assert_v0_contract

# 기존 엔진들
from app.engines.stt.engine import run_stt
from app.engines.voice.engine import run_voice
from app.engines.llm.engine import run_content
from app.engines.visual.engine import run_visual 


# visual_engine 싱글톤이 있을 수 있음 (네가 올린 코드엔 있음)
try:
    from app.engines.visual.engine import visual_engine as _visual_engine
except Exception:
    _visual_engine = None


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


def _wrap_visual_to_v0(raw: Any) -> Dict[str, Any]:
    """
    visual 엔진 반환값이 v0 계약이 아닐 경우,
    v0 형태로 강제로 래핑해서 run_all_test가 계속 돌게 만든다.

    기대 v0 형태(대략):
      {"module":"visual","metrics":{...},"events":[],"error":None}
    """
    # 이미 v0면 그대로
    if isinstance(raw, dict) and raw.get("module") == "visual" and "metrics" in raw:
        raw.setdefault("events", [])
        raw.setdefault("error", None)
        return raw

    # 새 엔진 형태(너가 올린 analyze 결과):
    # {"score": int, "feedback": str, "details": {...}} 또는 {"error": "..."}
    if isinstance(raw, dict):
        if "error" in raw and raw["error"]:
            return {
                "module": "visual",
                "metrics": {},
                "events": [],
                "error": str(raw["error"]),
            }

        score = raw.get("score")
        feedback = raw.get("feedback")
        details = raw.get("details", {})

        metrics: Dict[str, Any] = {}
        # score/feedback/details가 있으면 metrics로 넣어준다
        if score is not None:
            metrics["visual_score"] = score
        if feedback is not None:
            metrics["feedback"] = feedback
        if isinstance(details, dict):
            # details는 그대로 넣되 너무 크면 잘라서 넣는 것도 가능
            metrics.update(details)

        return {
            "module": "visual",
            "metrics": metrics,
            "events": [],  # 현재 v3 로직에 이벤트 구조 없으니 빈 리스트
            "error": None,
        }

    # 그 외 타입이면 에러로 래핑
    return {
        "module": "visual",
        "metrics": {},
        "events": [],
        "error": f"Unsupported visual output type: {type(raw)}",
    }


def run_visual_compat(video_path: str) -> Dict[str, Any]:
    """
    1) 기존 run_visual이 있으면 먼저 호출
    2) 없거나 결과가 v0가 아니면 visual_engine.analyze 사용
    3) 어떤 경우든 v0 계약으로 래핑해서 반환
    """
    # 1) 기존 run_visual 시도
    if run_visual is not None:
        try:
            out = run_visual(video_path)
            return _wrap_visual_to_v0(out)
        except Exception as e:
            # run_visual이 존재하지만 내부에서 터지는 경우 → fallback
            if _visual_engine is None:
                return _wrap_visual_to_v0({"error": f"run_visual failed: {e}"})

    # 2) 새 엔진(analyze)로 fallback
    if _visual_engine is not None:
        try:
            out = _visual_engine.analyze(video_path)
            return _wrap_visual_to_v0(out)
        except Exception as e:
            return _wrap_visual_to_v0({"error": f"visual_engine.analyze failed: {e}"})

    # 둘 다 없으면
    return _wrap_visual_to_v0({"error": "No visual runner found (run_visual and visual_engine missing)"})


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
        visual_out = timed("visual", run_visual_compat, video_path)
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
