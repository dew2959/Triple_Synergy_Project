from typing import Any, Dict
from app.engines.common.result import ok_result, error_result

def run_voice(audio_path: str) -> Dict[str, Any]:
    """
    Voice 엔진 stub (v0 규격 반환)
    - 아직 실제 분석 전: metrics/events 비움
    """
    try:
        if not audio_path:
            raise ValueError("audio_path is required")

        # TODO: 실제 voice 분석 지표 추가 예정
        metrics: Dict[str, Any] = {}
        events = []
        return ok_result("voice", metrics=metrics, events=events)

    except Exception as e:
        return error_result("voice", error_type="VOICE_ERROR", message=str(e))
