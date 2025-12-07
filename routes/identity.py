# routes/identity.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.location_identity import (
    get_location_summary,
    get_full_address,
    get_nearest_landmark,
    get_nearest_facility,
    CATEGORIES,   # ✅ facility code 검증용
)
from core.warning import warning_manager

router = APIRouter()


# =======================
# 요청 스키마
# =======================

class LocationRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90, description="위도")
    lng: float = Field(..., ge=-180, le=180, description="경도")

class FacilityRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    category_code: str = Field(..., description="Kakao category code")


# =======================
# ✅ 현재 위치 요약
# =======================

@router.post("/summary")
def location_summary(payload: LocationRequest):
    try:
        msg = get_location_summary(payload.lat, payload.lng)
        return {"mode": "summary", "message": msg}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"[summary] {str(e)}")


# =======================
# ✅ 상세 주소
# =======================

@router.post("/address")
def location_address(payload: LocationRequest):
    try:
        msg = get_full_address(payload.lat, payload.lng)
        return {"mode": "address", "message": msg}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"[address] {str(e)}")


# =======================
# ✅ 주변 건물
# =======================

@router.post("/landmark")
def location_landmark(payload: LocationRequest):
    try:
        msg = get_nearest_landmark(payload.lat, payload.lng)
        return {"mode": "landmark", "message": msg}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"[landmark] {str(e)}")


# =======================
# ✅ 시설 검색
# =======================

@router.post("/facility")
def location_facility(payload: FacilityRequest):

    if payload.category_code not in CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 시설 코드입니다: {payload.category_code}"
        )

    try:
        msg = get_nearest_facility(payload.lat, payload.lng, payload.category_code)
        return {
            "mode": "facility",
            "facility": CATEGORIES[payload.category_code],
            "message": msg
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"[facility] {str(e)}")


# =======================
# ✅ 현재 시스템 상태 (디버그)
# =======================

@router.get("/status")
def identity_status():
    return {
        "active_warnings": warning_manager.get_active_warnings(),
        "environment": warning_manager.last_env
    }
