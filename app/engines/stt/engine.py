from typing import Any, Dict
from app.engines.common.result import ok_result, error_result

def run_stt(audio_path: str) -> Dict[str, Any]:
    """
    STT 엔진 stub (v0 규격 반환)
    - 아직 실제 STT 전: metrics/events 비움
    """
    try:
        if not audio_path:
            raise ValueError("audio_path is required")

        # TODO: STT 결과 텍스트/신뢰도 등을 metrics(또는 artifacts)로 확장 예정
        metrics: Dict[str, Any] = {}
        events = []
        return ok_result("stt", metrics=metrics, events=events)

    except Exception as e:
        return error_result("stt", error_type="STT_ERROR", message=str(e))
