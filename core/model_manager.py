# core/model_manager.py

import logging
from typing import Optional, Dict, Any, Tuple

import torch
import numpy as np

from core.config import settings
from models.object_detector import ObjectDetector
from models.env_segmenter import EnvSegmenter


# -------------------------
# 로깅 설정
# -------------------------
logging.basicConfig(
    level=logging.WARNING,
    format="[%(asctime)s] [%(levelname)s] %(message)s"
)


# -------------------------
# 전역 모델 인스턴스
# -------------------------
_object_detector: Optional[ObjectDetector] = None
_env_segmenter: Optional[EnvSegmenter] = None

_prev_objects: Dict[int, Dict[str, Any]] = {}   # id -> {"h": int, "center": (x, y)}


# -------------------------
# 디바이스 자동 설정
# -------------------------
def get_device() -> str:
    if settings.DEVICE == "cpu":
        return "cpu"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


# -------------------------
# 모델 로딩
# -------------------------
def load_models() -> None:
    global _object_detector, _env_segmenter

    device = get_device()
    logging.info(f"Using device: {device}")

    # ---------- Object Detector ----------
    try:
        logging.info("Loading Object Detector...")
        _object_detector = ObjectDetector(
            weights_path=str(settings.OBJECT_DETECTOR_WEIGHTS),
            device=device,
            tracking=True   # ✅ tracking 모드 활성화
        )
        logging.info("Object Detector loaded successfully.")
    except Exception as e:
        logging.error(f"Object Detector load failed: {e}")
        # fallback: 더미 모델
        _object_detector = ObjectDetector(
            weights_path=None,
            device="cpu",
            dummy=True
        )

    # ---------- Env Segmenter ----------
    try:
        logging.info("Loading Env Segmenter...")
        _env_segmenter = EnvSegmenter(
            weights_path=str(settings.ENV_SEGMENTER_WEIGHTS),
            device=device
        )
        logging.info("Env Segmenter loaded successfully.")
    except Exception as e:
        logging.error(f"Env Segmenter load failed: {e}")
        # fallback: 더미 모델
        _env_segmenter = EnvSegmenter(
            weights_path=None,
            device="cpu",
            dummy=True
        )


# -------------------------
# 모델 Getter
# -------------------------
def get_object_detector() -> ObjectDetector:
    if _object_detector is None:
        raise RuntimeError("ObjectDetector not initialized. Call load_models() first.")
    return _object_detector


def get_env_segmenter() -> EnvSegmenter:
    if _env_segmenter is None:
        raise RuntimeError("EnvSegmenter not initialized. Call load_models() first.")
    return _env_segmenter


# -------------------------
# bbox 유틸
# -------------------------
def bbox_center(bbox: Tuple[float, float, float, float]) -> Tuple[int, int]:
    x1, y1, x2, y2 = bbox
    return int((x1 + x2) / 2), int((y1 + y2) / 2)


# -------------------------
# 공통 추론 함수 (TRACKING VERSION)
# -------------------------
def run_full_inference(image_bgr: np.ndarray) -> Dict[str, Any]:
    """
    tracking 기반 객체 추적 + 상태 정보 제공

    반환 형식 예:
    {
        "objects": [
            {
                "id": 1,
                "class": "car",
                "score": 0.91,
                "bbox": [x1, y1, x2, y2],
                "prev_h": 120,
                "curr_h": 140,
                "prev_center": (cx_prev, cy_prev),
                "curr_center": (cx_curr, cy_curr),
            },
            ...
        ],
        "environment": {
            ...  # EnvSegmenter 결과 (env_risk에서 사용)
        }
    }
    """
    global _prev_objects

    detector = get_object_detector()
    segmenter = get_env_segmenter()

    # -------------------
    # ✅ Tracking inference
    # -------------------
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

            # ✅ tracking feature
            "prev_h": prev_h,
            "curr_h": h,
            "prev_center": prev_center,
            "curr_center": center,
        })

    # -------------------
    # env model
    # -------------------
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
