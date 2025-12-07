# routes/inference.py

from fastapi import APIRouter, UploadFile, File, HTTPException, Body
from fastapi.responses import JSONResponse
import numpy as np
import cv2
import base64
import logging
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
# 파일 검증
# ------------------------
def validate_file(file: UploadFile):
    print("🔍 [DEBUG] filename =", file.filename)
    
    ext = file.filename.split(".")[-1].lower()
    print("🔍 [DEBUG] ext =", ext)
    print("🔍 [DEBUG] ALLOW_EXTENSIONS =", settings.ALLOW_EXTENSIONS)

    max_bytes = settings.MAX_IMAGE_SIZE_MB * 1024 * 1024
    if file.size is not None:
        print("🔍 [DEBUG] file.size =", file.size)

    # 👇⚠ 테스트 중이므로 일단 검증 중단
    return



# ------------------------
# 이미지 디코딩
# ------------------------
def read_image(file_bytes: bytes):
    np_arr = np.frombuffer(file_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="이미지를 디코딩할 수 없습니다.")
    return img


# ------------------------
# bbox 시각화
# ------------------------
def draw_boxes(image, objects):
    for obj in objects:
        if "bbox" not in obj:
            continue
        x1, y1, x2, y2 = map(int, obj["bbox"])
        label = obj.get("class", "obj")
        score = obj.get("score", 0.0)
        cv2.rectangle(image, (x1, y1), (x2, y2), (0,255,0), 2)
        cv2.putText(image, f"{label} {score:.2f}",
                    (x1, max(20, y1-10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)


# ------------------------
# 자동 경고 우선순위 점수
# ------------------------
def compute_priority(obj, frame_h):
    class_weight = CLASS_WEIGHTS.get(obj["class"], 0.5)
    distance_score = obj["curr_h"] / frame_h
    return class_weight * 2 + distance_score


# ------------------------
# 이미지 업로드 인퍼런스
# ------------------------
@router.post("/infer")
async def infer_image(file: UploadFile = File(...), mode: str = "realtime"):

    validate_file(file)
    file_bytes = await file.read()
    image_bgr = read_image(file_bytes)
    frame_h, frame_w, _ = image_bgr.shape

    result = run_full_inference(image_bgr)
    print("✅ [DEBUG] infer() ENTERED")
    logging.warning("[DEBUG] FULL INFERENCE RESULT = %s", result)
    environment = result.get("environment", {})

    if isinstance(environment, dict):
        warning_manager.last_env = environment

    env_risk = compute_env_risk(environment)
    objects = result.get("objects", [])
    for obj in objects:
        logging.warning("[DEBUG] RAW OBJ = %s", obj)  # ✅ 이 줄 추가

    # ✅ 자동 경고 후보
    danger_candidates = []

    # ----------------------
    # 객체 위험 분석
    # ----------------------
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
            "frame_w": frame_w
        }

        risk = compute_risk(state)
        is_approaching = (
            risk["components"]["Da"] == 1.0 and
            risk["components"]["Ad"] > 0
        )

        event = warning_manager.update_object(obj_id, cls_name, is_approaching)

        # ✅ 경고 후보 수집
        if event and warning_manager.should_warn(event):
            score = compute_priority(obj, frame_h)
            danger_candidates.append({
                "cls": cls_name,
                "center": curr_center,
                "score": score
            })

    warnings = []

    # ----------------------
    # ✅ 전역 쿨다운 통과 시에만 자동 경고
    # ----------------------
    if danger_candidates and warning_manager.can_global_warn():
        top = sorted(danger_candidates, key=lambda x: x["score"], reverse=True)[0]
        center_x = top["center"][0] if top["center"] else frame_w/2
        msg = build_warning_message(top["cls"], center_x, frame_w)
        warnings.append(msg)
        logging.warning(f"[AUTO WARNING] {msg}")

    # ----------------------
    # 환경 위험 자동 경고
    # ----------------------
    if env_risk["is_danger"]:
        for zone in env_risk["danger_zones"]:
            if warning_manager.should_env_warn(zone):
                label = TTS_CLASS_MAP.get(zone, zone)
                warnings.append(f"{label} 환경입니다. 주의하세요.")

    warning_manager.cleanup()
    result["warnings"] = warnings


    # --------------------------
    # 이미지 시각화 (업로드)
    # --------------------------
    if mode == "upload":
        image_vis = image_bgr.copy()
        draw_boxes(image_vis, objects)
        _, buffer = cv2.imencode(".jpg", image_vis)
        encoded = base64.b64encode(buffer).decode("utf-8")
        result["image"] = encoded
    else:
        result["image"] = None

    # --------------------------
    # 응답 슬림화
    # --------------------------
    for obj in objects:
        obj.pop("prev_center", None)
        obj.pop("curr_center", None)
        obj.pop("prev_h", None)
        obj.pop("curr_h", None)

    return JSONResponse(content=result)


# ==================================================
# ✅ 수동 객체 안내 (거리 기준 상위 3개 + 사람형 문장)
# ==================================================
@router.get("/nearby_objects")
def get_nearby_objects():

    objs = warning_manager.get_all_objects()
    if not objs:
        return {"message": "현재 근처에 감지된 객체가 없습니다.", "objects": []}

    # 가까운 순 정렬 (bbox 높이 기준)
    sorted_objs = sorted(objs, key=lambda o: o.last_seen, reverse=True)[:3]

    labels = [TTS_CLASS_MAP.get(o.cls, o.cls) for o in sorted_objs]
    count = Counter(labels)

    parts = []
    for k, v in count.items():
        unit = "명" if k == "사람" else "대"
        parts.append(f"{k} {v}{unit}")

    msg = "현재 근처에 " + ", ".join(parts) + "가 있습니다."
    return {"message": msg, "objects": parts}


# ==================================================
# ✅ 수동 위험 환경 안내
# ==================================================
@router.get("/env/danger")
def get_env_danger():

    env = warning_manager.last_env
    if not env:
        return {"message": "환경 정보를 인식할 수 없습니다."}

    env_risk = compute_env_risk(env)
    danger = env_risk.get("danger_zones", [])

    if not danger:
        return {"message": "현재 근처에 위험한 환경은 없습니다."}

    zone = danger[0]
    direction = "정면"
    label = add_particle(TTS_CLASS_MAP.get(zone, zone))
    return {"message": f"현재 {direction}에 {label} 있습니다."}


# ==================================================
# ✅ 수동 안전 환경 안내
# ==================================================
@router.get("/env/safe")
def get_env_safe():

    env = warning_manager.last_env
    if not env:
        return {"message": "환경 정보를 인식할 수 없습니다."}

    env_risk = compute_env_risk(env)
    safe = env_risk.get("safe_zones", [])

    if not safe:
        return {"message": "현재 근처에 안전한 환경은 없습니다."}

    zone = safe[0]
    direction = "정면"
    label = add_particle(TTS_CLASS_MAP.get(zone, zone))
    return {"message": f"현재 {direction}에 {label} 있습니다."}


# ------------------------
# 헬스 체크
# ------------------------
@router.get("/health")
def health_check():
    return {"status": "ok", "message": "Inference API is running"}


# ------------------------
# 환경 경고 전체 on/off (UI 토글용)
# ------------------------
@router.post("/env/toggle")
def toggle_env_alert():
    if warning_manager.env_alert_enabled:
        warning_manager.disable_env_alerts()
        return {"enabled": False, "message": "환경 경고를 끕니다."}
    else:
        warning_manager.enable_env_alerts()
        return {"enabled": True, "message": "환경 경고를 켭니다."}
