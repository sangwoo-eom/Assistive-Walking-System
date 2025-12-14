import logging
from typing import Optional, Dict, Any, Tuple

import torch
import numpy as np

from core.config import settings
from models.object_detector import ObjectDetector
from models.env_segmenter import EnvSegmenter


logging.basicConfig(
    level=logging.WARNING,
    format="[%(asctime)s] [%(levelname)s] %(message)s"
)

_object_detector: Optional[ObjectDetector] = None
_env_segmenter: Optional[EnvSegmenter] = None

_prev_objects: Dict[int, Dict[str, Any]] = {}  # id -> {"h": int, "center": (x, y)}


def get_device() -> str:
    if settings.DEVICE == "cpu":
        return "cpu"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def load_models() -> None:
    global _object_detector, _env_segmenter

    device = get_device()
    logging.info(f"Using device: {device}")

    try:
        _object_detector = ObjectDetector(
            weights_path=str(settings.OBJECT_DETECTOR_WEIGHTS),
            device=device,
            tracking=True
        )
    except Exception as e:
        logging.error(f"Object Detector load failed: {e}")
        _object_detector = ObjectDetector(
            weights_path=None,
            device="cpu",
            dummy=True
        )

    try:
        _env_segmenter = EnvSegmenter(
            weights_path=str(settings.ENV_SEGMENTER_WEIGHTS),
            device=device
        )
    except Exception as e:
        logging.error(f"Env Segmenter load failed: {e}")
        _env_segmenter = EnvSegmenter(
            weights_path=None,
            device="cpu",
            dummy=True
        )


def get_object_detector() -> ObjectDetector:
    if _object_detector is None:
        raise RuntimeError("ObjectDetector not initialized. Call load_models() first.")
    return _object_detector


def get_env_segmenter() -> EnvSegmenter:
    if _env_segmenter is None:
        raise RuntimeError("EnvSegmenter not initialized. Call load_models() first.")
    return _env_segmenter


def bbox_center(bbox: Tuple[float, float, float, float]) -> Tuple[int, int]:
    x1, y1, x2, y2 = bbox
    return int((x1 + x2) / 2), int((y1 + y2) / 2)


def run_full_inference(image_bgr: np.ndarray) -> Dict[str, Any]:
    """
    tracking 기반 객체 추적 결과와 환경 인식 결과를 함께 반환
    """
    global _prev_objects

    detector = get_object_detector()
    segmenter = get_env_segmenter()

    det_result = detector.predict(image_bgr, track=True) or {}
    objects = det_result.get("objects", []) or []

    enriched = []

    for obj in objects:
        obj_id = obj.get("id")
        bbox = obj.get("bbox")
        cls_name = obj.get("class")
        score = obj.get("score")

        if obj_id is None or bbox is None or len(bbox) != 4:
            continue

        x1, y1, x2, y2 = bbox
        center = bbox_center(tuple(bbox))
        h = y2 - y1

        prev = _prev_objects.get(obj_id)
        prev_h = prev["h"] if prev else None
        prev_center = prev["center"] if prev else None

        _prev_objects[obj_id] = {"h": h, "center": center}

        enriched.append({
            "id": obj_id,
            "class": cls_name,
            "score": score,
            "bbox": bbox,
            "prev_h": prev_h,
            "curr_h": h,
            "prev_center": prev_center,
            "curr_center": center,
        })

    env: Dict[str, Any] = {}
    try:
        env_result = segmenter.predict(image_bgr)
        if isinstance(env_result, dict):
            env = env_result.get("env", {}) or {}
    except NotImplementedError:
        env = {}
    except Exception as e:
        logging.error(f"EnvSegmenter inference error: {e}")
        env = {}

    return {
        "objects": enriched,
        "environment": env
    }
