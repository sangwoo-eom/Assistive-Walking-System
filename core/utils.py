# core/utils.py

import cv2
import numpy as np
from typing import List, Tuple, Dict, Any


# -----------------------------
# 위험 판단 파라미터
# -----------------------------
RISK_DISTANCE_THRESHOLD = 0.25   # bbox 높이 / 이미지 높이


# -----------------------------
# 거리 기반 위험도 판단
# -----------------------------
def is_close_enough(box: Tuple[float, float, float, float], frame_h: int):
    """
    bbox 높이가 프레임 대비 충분히 크면
    '가까이 있다'고 간단히 판단
    """
    if frame_h <= 0:
        return False, 0.0

    x1, y1, x2, y2 = box
    h = y2 - y1
    ratio = h / frame_h
    return ratio > RISK_DISTANCE_THRESHOLD, ratio


# -----------------------------
# bbox 그리기 (JSON 결과 기반)
# -----------------------------
def draw_detections(frame: np.ndarray, objects: List[Dict[str, Any]]) -> np.ndarray:
    """
    model_manager가 반환한 JSON 결과 기반 시각화

    objects = [
        {"class": "car", "score": 0.9, "bbox": [x1,y1,x2,y2]},
        ...
    ]
    """

    if frame is None or frame.size == 0:
        return frame

    h, w, _ = frame.shape

    for obj in objects:
        bbox = obj.get("bbox")
        cls = obj.get("class", "obj")
        conf = obj.get("score", 0.0)

        if bbox is None or len(bbox) != 4:
            continue

        x1, y1, x2, y2 = map(int, bbox)

        # 위험 판단
        is_risk, ratio = is_close_enough((x1, y1, x2, y2), h)

        if is_risk:
            color = (0, 0, 255)
            extra = " DANGER"
        else:
            color = (0, 255, 0)
            extra = ""

        label = f"{cls} {conf:.2f}{extra}"

        # bbox
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        # text background
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw, y1), color, -1)

        # text
        cv2.putText(
            frame,
            label,
            (x1, y1 - 4),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2,
        )

    return frame
