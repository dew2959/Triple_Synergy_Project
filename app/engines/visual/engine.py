from typing import Any, Dict, List, Optional
from engines.common.result import ok_result, error_result

def run_visual(
    video_path: str,
    # 필요하면 model_path, target_fps 등 추가
) -> Dict[str, Any]:
    """
    Visual 엔진은 v0 계약에 맞춰 dict를 반환한다.
    오늘 목표: metrics 3개(face_presence_ratio, head_center_ratio, head_movement_std)만 반환.
    events는 일단 []로 둔다(추후 확장).
    """
    try:
        # TODO: 여기에서 네 mediapipe facemesh 코드로 실제 계산
        # 아래 값들은 지금은 더미 / 또는 계산 결과로 교체
        face_presence_ratio = 1.0
        head_center_ratio = 0.5
        head_movement_std = 0.6

        metrics = {
            "face_presence_ratio": float(face_presence_ratio),
            "head_center_ratio": float(head_center_ratio),
            "head_movement_std": float(head_movement_std),
        }
        return ok_result("visual", metrics=metrics, events=[])

    except Exception as e:
        return error_result("visual", err_type="VISUAL_ERROR", message=str(e))
