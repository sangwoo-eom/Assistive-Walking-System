# core/risk.py

from typing import Dict, Any


CLASS_WEIGHTS: Dict[str, float] = {
    "car": 1.0,
    "bus": 1.0,
    "truck": 1.0,
    "motorcycle": 0.9,
    "scooter": 0.9,
    "bicycle": 0.7,
}


def compute_ttc(prev_h: float, curr_h: float) -> float:
    """
    프레임 간 bbox 높이 변화 기반 TTC(Time-To-Collision) 근사.
    prev_h 또는 curr_h가 비정상(<=0)이면 무한대 취급.
    """
    if prev_h is None or curr_h is None or prev_h <= 0 or curr_h <= 0:
        return float("inf")

    dh = curr_h - prev_h
    if dh <= 0:
        return float("inf")
    return curr_h / dh


def compute_Tr(ttc: float) -> float:
    """
    TTC 기반 위험도 계수.
    """
    if ttc < 2.0:
        return 1.0
    elif ttc < 5.0:
        return 0.5
    else:
        return 0.0


def compute_Da(prev_h: float, curr_h: float, threshold: float = 0.05) -> float:
    """
    거리(크기) 증가 여부 계수.
    prev_h가 0 또는 None이면 보수적으로 0 처리.
    """
    if prev_h is None or curr_h is None or prev_h <= 0:
        return 0.0
    growth = (curr_h - prev_h) / prev_h
    return 1.0 if growth >= threshold else 0.0


def compute_Ad(prev_center, curr_center, frame_w: int) -> float:
    """
    화면 중앙 방향으로 다가오는지 여부.
    - 중앙 쪽으로 확실히 접근: 1.0
    - 거의 변화 없음: 0.3
    - 그 외: 0.0
    """
    if (
        prev_center is None
        or curr_center is None
        or frame_w is None
        or frame_w <= 0
    ):
        return 0.0

    prev_x, _ = prev_center
    curr_x, _ = curr_center

    center_delta = curr_x - prev_x
    toward_center = abs(curr_x - frame_w / 2) < abs(prev_x - frame_w / 2)

    if toward_center:
        return 1.0
    elif abs(center_delta) < 5:
        return 0.3
    else:
        return 0.0


def compute_risk(obj: Dict[str, Any]) -> Dict[str, Any]:
    """
    obj = {
        "class": str,
        "prev_h": float,
        "curr_h": float,
        "prev_center": (x,y) | None,
        "curr_center": (x,y) | None,
        "frame_w": int
    }
    """

    cls_name = obj.get("class", "")
    prev_h = obj.get("prev_h")
    curr_h = obj.get("curr_h")
    prev_center = obj.get("prev_center")
    curr_center = obj.get("curr_center")
    frame_w = obj.get("frame_w", 0)

    wc = CLASS_WEIGHTS.get(cls_name, 0.0)

    Da = compute_Da(prev_h, curr_h)
    Ad = compute_Ad(prev_center, curr_center, frame_w)
    ttc = compute_ttc(prev_h, curr_h)
    Tr = compute_Tr(ttc)

    R = wc * Da * Ad * Tr

    return {
        "risk_score": R,
        "components": {
            "Wc": wc,
            "Da": Da,
            "Ad": Ad,
            "Tr": Tr,
            "TTC": ttc,
        },
    }
