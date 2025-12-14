# routes/inference.py

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import numpy as np
import cv2
import base64
import logging
import time
from collections import Counter

from core.tts import build_warning_message, TTS_CLASS_MAP
from core.model_manager import run_full_inference
from core.config import settings
from core.risk import compute_risk, CLASS_WEIGHTS
from core.warning import warning_manager
from core.env_risk import compute_env_risk
from core.tts import get_direction, add_particle

router = APIRouter()


# ------------------------
# File validation
# ------------------------
def validate_file(file: UploadFile):
    # Debug information (temporary)
    print("[DEBUG] filename =", file.filename)

    ext = file.filename.split(".")[-1].lower()
    print("[DEBUG] ext =", ext)
    print("[DEBUG] ALLOW_EXTENSIONS =", settings.ALLOW_EXTENSIONS)

    max_bytes = settings.MAX_IMAGE_SIZE_MB * 1024 * 1024
    if file.size is not None:
        print("[DEBUG] file.size =", file.size)

    # Validation is intentionally bypassed during testing
    return


# ------------------------
# Image decoding
# ------------------------
def read_image(file_bytes: bytes):
    np_arr = np.frombuffer(file_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Failed to decode image.")
    return img


# ------------------------
# Bounding box visualization
# ------------------------
def draw_boxes(image, objects):
    for obj in objects:
        if "bbox" not in obj:
            continue
        x1, y1, x2, y2 = map(int, obj["bbox"])
        label = obj.get("class", "obj")
        score = obj.get("score", 0.0)
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(
            image,
            f"{label} {score:.2f}",
            (x1, max(20, y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2,
        )


# ------------------------
# Priority score for automatic warnings
# ------------------------
def compute_priority(obj, frame_h):
    class_weight = CLASS_WEIGHTS.get(obj["class"], 0.5)
    distance_score = obj["curr_h"] / frame_h
    return class_weight * 2 + distance_score


# ------------------------
# Image inference endpoint
# ------------------------
@router.post("/infer")
async def infer_image(file: UploadFile = File(...), mode: str = "realtime"):
    print("[DEBUG] MODE RECEIVED =", mode)

    # Latency measurement (start)
    t_start = time.perf_counter()

    validate_file(file)
    file_bytes = await file.read()
    image_bgr = read_image(file_bytes)
    frame_h, frame_w, _ = image_bgr.shape

    # Model inference timing
    t_inf_start = time.perf_counter()
    result = run_full_inference(image_bgr)
    t_inf_end = time.perf_counter()

    print("[DEBUG] infer() entered")
    logging.warning("[DEBUG] FULL INFERENCE RESULT = %s", result)

    environment = result.get("environment", {})
    if isinstance(environment, dict):
        warning_manager.last_env = environment

    env_risk = compute_env_risk(environment)
    objects = result.get("objects", [])

    # Risk evaluation logic timing
    t_logic_start = time.perf_counter()

    danger_candidates = []

    for obj in objects:
        obj_id = obj.get("id")
        cls_name = obj.get("class")
        prev_h = obj.get("prev_h")
        curr_h = obj.get("curr_h")
        prev_center = obj.get("prev_center")
        curr_center = obj.get("curr_center")

        if None in [obj_id, cls_name, prev_h, curr_h, prev_center, curr_center]:
            continue

        state = {
            "class": cls_name,
            "prev_h": prev_h,
            "curr_h": curr_h,
            "prev_center": prev_center,
            "curr_center": curr_center,
            "frame_w": frame_w,
        }

        risk = compute_risk(state)
        is_approaching = (
            risk["components"]["Da"] == 1.0 and
            risk["components"]["Ad"] > 0
        )

        event = warning_manager.update_object(obj_id, cls_name, is_approaching)

        if event and warning_manager.should_warn(event):
            score = compute_priority(obj, frame_h)
            danger_candidates.append({
                "cls": cls_name,
                "center": curr_center,
                "score": score,
            })

    warnings = []

    if danger_candidates and warning_manager.can_global_warn():
        top = sorted(danger_candidates, key=lambda x: x["score"], reverse=True)[0]
        center_x = top["center"][0] if top["center"] else frame_w / 2
        msg = build_warning_message(top["cls"], center_x, frame_w)
        warnings.append(msg)

    if env_risk["is_danger"]:
        for zone in env_risk["danger_zones"]:
            if warning_manager.should_env_warn(zone):
                label = TTS_CLASS_MAP.get(zone, zone)
                warnings.append(f"{label} environment detected. Please be cautious.")

    warning_manager.cleanup()
    result["warnings"] = warnings

    t_logic_end = time.perf_counter()

    # Visualization for upload mode
    if mode == "upload":
        image_vis = image_bgr.copy()
        draw_boxes(image_vis, objects)
        _, buffer = cv2.imencode(".jpg", image_vis)
        encoded = base64.b64encode(buffer).decode("utf-8")
        result["image"] = encoded
        print("[DEBUG] upload mode image generated:", encoded is not None)
    else:
        result["image"] = None
        print("[DEBUG] realtime mode, no image returned")

    for obj in objects:
        obj.pop("prev_center", None)
        obj.pop("curr_center", None)
        obj.pop("prev_h", None)
        obj.pop("curr_h", None)

    # Latency summary
    t_end = time.perf_counter()
    latency = {
        "total_ms": round((t_end - t_start) * 1000, 2),
        "inference_ms": round((t_inf_end - t_inf_start) * 1000, 2),
        "logic_ms": round((t_logic_end - t_logic_start) * 1000, 2),
    }

    result["latency"] = latency
    logging.warning(f"[LATENCY] {latency}")

    return JSONResponse(content=result)


# ------------------------
# Manual nearby object summary
# ------------------------
@router.get("/nearby_objects")
def get_nearby_objects():
    objs = warning_manager.get_all_objects()
    if not objs:
        return {"message": "No nearby objects detected.", "objects": []}

    sorted_objs = sorted(objs, key=lambda o: o.last_seen, reverse=True)[:3]

    labels = [TTS_CLASS_MAP.get(o.cls, o.cls) for o in sorted_objs]
    count = Counter(labels)

    parts = []
    for k, v in count.items():
        unit = "persons" if k == "사람" else "units"
        parts.append(f"{k} {v}{unit}")

    msg = "Nearby objects detected: " + ", ".join(parts)
    return {"message": msg, "objects": parts}


# ------------------------
# Manual environment danger query
# ------------------------
@router.get("/env/danger")
def get_env_danger():
    env = warning_manager.last_env
    if not env:
        return {"message": "Environment information is unavailable."}

    env_risk = compute_env_risk(env)
    danger = env_risk.get("danger_zones", [])

    if not danger:
        return {"message": "No dangerous environment detected nearby."}

    zone = danger[0]
    direction = "front"
    label = add_particle(TTS_CLASS_MAP.get(zone, zone))
    return {"message": f"{label} detected {direction}."}


# ------------------------
# Manual environment safe query
# ------------------------
@router.get("/env/safe")
def get_env_safe():
    env = warning_manager.last_env
    if not env:
        return {"message": "Environment information is unavailable."}

    env_risk = compute_env_risk(env)
    safe = env_risk.get("safe_zones", [])

    if not safe:
        return {"message": "No safe environment detected nearby."}

    zone = safe[0]
    direction = "front"
    label = add_particle(TTS_CLASS_MAP.get(zone, zone))
    return {"message": f"{label} detected {direction}."}


# ------------------------
# Health check
# ------------------------
@router.get("/health")
def health_check():
    return {"status": "ok", "message": "Inference API is running"}


# ------------------------
# Environment alert toggle (UI control)
# ------------------------
@router.post("/env/toggle")
def toggle_env_alert():
    if warning_manager.env_alert_enabled:
        warning_manager.disable_env_alerts()
        return {"enabled": False, "message": "Environment alerts disabled."}
    else:
        warning_manager.enable_env_alerts()
        return {"enabled": True, "message": "Environment alerts enabled."}
