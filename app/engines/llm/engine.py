from typing import Any, Dict
from app.engines.common.result import ok_result, error_result

def run_content(text: str) -> Dict[str, Any]:
    """
    Content 엔진 stub (v0 규격 반환)
    - 아직 실제 분석 전: metrics/events 비움
    """
    try:
        if text is None or text == "":
            raise ValueError("text is required")

        # TODO: 내용 분석 지표(키워드, 구조 점수 등) metrics로 확장 예정
        metrics: Dict[str, Any] = {}
        events = []
        return ok_result("content", metrics=metrics, events=events)

    except Exception as e:
        return error_result("content", error_type="CONTENT_ERROR", message=str(e))
