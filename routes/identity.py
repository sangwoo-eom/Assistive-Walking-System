# routes/identity.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.location_identity import (
    get_location_summary,
    get_full_address,
    get_nearest_landmark,
    get_nearest_facility,
    CATEGORIES,   # Facility code validation
)
from core.warning import warning_manager

router = APIRouter()


# =======================
# Request schemas
# =======================

class LocationRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lng: float = Field(..., ge=-180, le=180, description="Longitude")


class FacilityRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    category_code: str = Field(..., description="Kakao category code")


# =======================
# Location summary
# =======================

@router.post("/summary")
def location_summary(payload: LocationRequest):
    try:
        msg = get_location_summary(payload.lat, payload.lng)
        return {"mode": "summary", "message": msg}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"[summary] {str(e)}")


# =======================
# Full address
# =======================

@router.post("/address")
def location_address(payload: LocationRequest):
    try:
        msg = get_full_address(payload.lat, payload.lng)
        return {"mode": "address", "message": msg}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"[address] {str(e)}")


# =======================
# Nearby landmark
# =======================

@router.post("/landmark")
def location_landmark(payload: LocationRequest):
    try:
        msg = get_nearest_landmark(payload.lat, payload.lng)
        return {"mode": "landmark", "message": msg}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"[landmark] {str(e)}")


# =======================
# Facility search
# =======================

@router.post("/facility")
def location_facility(payload: FacilityRequest):

    if payload.category_code not in CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported facility code: {payload.category_code}"
        )

    try:
        msg = get_nearest_facility(
            payload.lat,
            payload.lng,
            payload.category_code
        )
        return {
            "mode": "facility",
            "facility": CATEGORIES[payload.category_code],
            "message": msg
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"[facility] {str(e)}")


# =======================
# System status (debug)
# =======================

@router.get("/status")
def identity_status():
    return {
        "active_warnings": warning_manager.get_active_warnings(),
        "environment": warning_manager.last_env
    }
