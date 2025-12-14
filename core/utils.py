import cv2
import numpy as np
from typing import List, Tuple, Dict, Any


RISK_DISTANCE_THRESHOLD = 0.25  # bbox 높이 / 프레임 높이 비율


def is_close_enough(box: Tuple[float, float, float, float], frame_h: int):
    if frame_h <= 0:
        return False, 0.0

    x1, y1, x2, y2 = box
    h = y2 - y1
    ratio = h / frame_h
    return ratio > RISK_DISTANCE_THRESHOLD, ratio


def draw_detections(frame: np.ndarray, objects: List[Dict[str, Any]]) -> np.ndarray:
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

        is_risk, ratio = is_close_enough((x1, y1, x2, y2), h)

        if is_risk:
            color = (0, 0, 255)
            extra = " DANGER"
        else:
            color = (0, 255, 0)
            extra = ""

        label = f"{cls} {conf:.2f}{extra}"

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw, y1), color, -1)

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
