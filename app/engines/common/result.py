from typing import Any, Dict, List, Optional, Literal

ModuleName = Literal["visual", "voice", "stt", "content"]

def ok_result(
    module: ModuleName,
    metrics: Optional[Dict[str, Any]] = None,
    events: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    성공 결과를 표준 dict 형태로 반환한다.
    artifacts는 현재 v0에서는 옵션이며, 필요 시만 사용한다.
    """
    out: Dict[str, Any] = {
        "module": module,
        "metrics": metrics or {},
        "events": events or [],
        "error": None,
    }
    return out


def error_result(
    module: ModuleName,
    err_type: str,
    message: str,
    metrics: Optional[Dict[str, Any]] = None,
    events: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    실패 결과를 표준 dict 형태로 반환한다.
    실패해도 metrics/events는 타입 유지(dict/list) + 빈값 허용.
    """
    out: Dict[str, Any] = {
        "module": module,
        "metrics": metrics or {},
        "events": events or [],
        "error": {"type": err_type, "message": message},
    }
    return out