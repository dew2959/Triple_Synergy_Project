from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# 허용하는 module 값(엔진 이름) 목록
_ALLOWED_MODULES = {"visual", "voice", "stt", "content"}

# v0 계약에서 반드시 포함해야 하는 최상위 키들
_V0_KEYS = {"module", "metrics", "events", "error"}


def validate_v0_contract(
    out: Any,
    expected_module: Optional[str] = None,
) -> Tuple[bool, List[str]]:
    """
    v0 raw output contract validator

    Rules (요약):
    - out은 dict여야 하고, module/metrics/events/error 키가 있어야 한다.
    - metrics는 항상 dict 타입이어야 한다. (성공/실패 모두 dict)
    - events는 항상 list 타입이어야 한다. (성공/실패 모두 list)
    - error는 성공이면 None, 실패면 {"type": str, "message": str} 형태의 dict
    - 실패(error != None)라면 metrics는 {} / events는 [] 로 비워서 반환해야 한다.
    """
    errs: List[str] = []

    # 1) out이 dict인지 확인 (아니면 바로 실패 반환)
    if not isinstance(out, dict):
        return False, [f"Output must be dict, got {type(out).__name__}"]

    # 2) 필수 키(module/metrics/events/error)가 빠졌는지 체크
    missing = _V0_KEYS - set(out.keys())
    if missing:
        errs.append(f"Missing keys: {sorted(missing)}")

    # (선택) extra key는 허용하되, 계약을 엄격히 하고 싶으면 아래를 활성화
    # - 현재는 "필수 키만 있으면 OK"로 운용
    # extra = set(out.keys()) - _V0_KEYS
    # if extra:
    #     errs.append(f"Extra keys not allowed: {sorted(extra)}")

    # 3) module 타입/값 검증
    module = out.get("module")
    if not isinstance(module, str):
        errs.append(f"'module' must be str, got {type(module).__name__}")
    else:
        # 허용된 module 목록인지 확인
        if module not in _ALLOWED_MODULES:
            errs.append(f"'module' must be one of {_ALLOWED_MODULES}, got '{module}'")
        # 호출자가 expected_module을 지정한 경우, 일치 여부까지 확인
        if expected_module is not None and module != expected_module:
            errs.append(f"Expected module '{expected_module}', got '{module}'")

    # 4) metrics는 항상 dict여야 함
    metrics = out.get("metrics")
    if not isinstance(metrics, dict):
        errs.append(f"'metrics' must be dict, got {type(metrics).__name__}")

    # 5) events는 항상 list여야 함
    events = out.get("events")
    if not isinstance(events, list):
        errs.append(f"'events' must be list, got {type(events).__name__}")

    # 6) error 규칙 검증
    error = out.get("error")
    if error is not None:
        # 실패 케이스: error는 dict여야 하고 type/message 키가 있어야 함
        if not isinstance(error, dict):
            errs.append(f"'error' must be None or dict, got {type(error).__name__}")
        else:
            # error dict에 필요한 키가 있는지 확인
            if "type" not in error or "message" not in error:
                errs.append("'error' dict must include keys: 'type', 'message'")
            else:
                # type/message는 각각 str이어야 함
                if not isinstance(error.get("type"), str):
                    errs.append("'error.type' must be str")
                if not isinstance(error.get("message"), str):
                    errs.append("'error.message' must be str")

        # 7) 실패 시에는 metrics/events를 비워서 반환해야 한다는 규칙 체크
        if isinstance(metrics, dict) and metrics != {}:
            errs.append("On failure (error != None), 'metrics' must be {}")
        if isinstance(events, list) and events != []:
            errs.append("On failure (error != None), 'events' must be []")

    # 에러가 하나도 없으면 ok=True, 있으면 ok=False
    return (len(errs) == 0), errs


def assert_v0_contract(out: Any, expected_module: Optional[str] = None) -> None:
    """
    validate_v0_contract 결과가 실패면 AssertionError로 터뜨리는 헬퍼
    - 테스트/개발 단계에서 계약 위반을 빠르게 잡기 좋음
    """
    ok, errs = validate_v0_contract(out, expected_module=expected_module)
    if not ok:
        # 에러들을 보기 좋게 줄바꿈으로 묶어서 예외로 던짐
        msg = "v0 contract validation failed:\n- " + "\n- ".join(errs)
        raise AssertionError(msg)
