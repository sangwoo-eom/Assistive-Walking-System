# core/location_identity.py

from __future__ import annotations
import logging
import math
from typing import Any, Dict, List
import requests
from core.config import settings

logger = logging.getLogger(__name__)

KAKAO_KEY = settings.KAKAO_REST_API_KEY
BASE_URL = "https://dapi.kakao.com/v2/local"
HEADERS = {"Authorization": f"KakaoAK {KAKAO_KEY}"}


# ======================
# 거리 계산
# ======================

def _haversine(lng1, lat1, lng2, lat2):
    R = 6371000
    rad = math.radians
    return 2 * R * math.asin(
        math.sqrt(
            math.sin(rad(lat2-lat1)/2)**2 +
            math.cos(rad(lat1))*math.cos(rad(lat2))*math.sin(rad(lng2-lng1)/2)**2
        )
    )


# ======================
# Kakao API
# ======================

def _kakao_get(path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    if not KAKAO_KEY:
        logger.error("[location] Kakao API Key 누락")
        return {}

    try:
        r = requests.get(BASE_URL + path, headers=HEADERS, params=params, timeout=3)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.error(f"[KAKAO API ERROR] {e}")
        logger.error(f"URL = {BASE_URL + path}")
        logger.error(f"PARAMS = {params}")
        return {}


# ======================
# 좌표 검증
# ======================

def _validate_coords(lat, lng):
    if lat is None or lng is None:
        return False, "GPS 신호가 불안정합니다."

    if lat == 0 and lng == 0:
        return False, "위치 신호를 아직 받지 못했습니다."

    if abs(lat) > 90 or abs(lng) > 180:
        return False, "위치 정보가 비정상입니다."

    return True, None


# ======================
# 주소
# ======================

def _reverse_geocode(lat, lng):
    data = _kakao_get("/geo/coord2address.json", {"x": lng, "y": lat})
    docs = data.get("documents")
    return docs[0] if docs else {}


def _get_region_text(data: dict) -> str:
    """
    행정동까지만 추출:
    ex) 서울특별시 광진구 능동
    """
    r = data.get("address", {})
    r1 = r.get("region_1depth_name", "")
    r2 = r.get("region_2depth_name", "")
    r3 = r.get("region_3depth_name", "")

    return " ".join([x for x in [r1, r2, r3] if x])


# ======================
# 카테고리
# ======================

CATEGORIES = {
    "SW8": "지하철역",
    "HP8": "병원",
    "SC4": "학교",
    "PO3": "공공기관",
    "MT1": "대형마트",
    "CS2": "편의점",
    "FD6": "음식점",
    "PM9": "약국",
}

PRIORITY = {
    "SW8": 2000,
    "HP8": 1000,
    "SC4": 800,
    "PO3": 700,
    "DEFAULT": 400,
    "CROSSROAD": 200
}

SEARCH_RADIUS = {
    "SW8": 2000,
    "DEFAULT": 800
}


# ======================
# 카테고리 검색
# ======================

def _search_category(code, lat, lng):
    radius = SEARCH_RADIUS.get(code, SEARCH_RADIUS["DEFAULT"])

    data = _kakao_get("/search/category.json", {
        "category_group_code": code,
        "x": lng,
        "y": lat,
        "radius": radius,
        "sort": "distance",
        "size": 10
    })
    return data.get("documents", []), radius


# ======================
# 거리 + 점수
# ======================

def _score_poi(poi, lat, lng, weight):
    try:
        dist = _haversine(lng, lat, float(poi["x"]), float(poi["y"]))
        poi["_distance"] = dist
        poi["_score"] = weight - dist
        return poi
    except Exception:
        return None


# ======================
# POI 수집
# ======================

def _gather_pois(lat, lng) -> List[Dict]:
    results = []

    # 지하철 최우선
    subways, _ = _search_category("SW8", lat, lng)
    for p in subways:
        s = _score_poi(p, lat, lng, PRIORITY["SW8"])
        if s: results.append(s)

    # 주요 시설
    for code in ["HP8", "SC4", "PO3"]:
        items, _ = _search_category(code, lat, lng)
        for p in items:
            s = _score_poi(p, lat, lng, PRIORITY[code])
            if s: results.append(s)

    # 교차로 fallback
    crossroads = _kakao_get("/search/keyword.json", {
        "query": "사거리",
        "x": lng,
        "y": lat,
        "radius": 300,
        "size": 5
    }).get("documents", [])

    for p in crossroads:
        s = _score_poi(p, lat, lng, PRIORITY["CROSSROAD"])
        if s: results.append(s)

    return results


# ======================
# ✅ 위치 요약
# ======================

def get_location_summary(lat: float, lng: float) -> str:
    ok, msg = _validate_coords(lat, lng)
    if not ok:
        return msg

    region_data = _reverse_geocode(lat, lng)
    region_text = _get_region_text(region_data)

    pois = _gather_pois(lat, lng)
    if not pois:
        return f"현재 위치는 {region_text}으로, 주변에 안내할 주요 시설이 없습니다."

    best = max(pois, key=lambda x: x["_score"])
    name = best["place_name"]

    return f"현재 위치는 {region_text}으로, {name} 근처입니다."


# ======================
# ✅ 상세 주소
# ======================

def get_full_address(lat: float, lng: float) -> str:
    ok, msg = _validate_coords(lat, lng)
    if not ok:
        return msg

    data = _reverse_geocode(lat, lng)
    road = data.get("road_address", {})
    addr = data.get("address", {})

    if road.get("address_name"):
        return road["address_name"]

    if addr.get("address_name"):
        return addr["address_name"]

    return "상세 주소를 불러올 수 없습니다."


# ======================
# ✅ 주변 건물
# ======================

def get_nearest_landmark(lat: float, lng: float) -> str:
    ok, msg = _validate_coords(lat, lng)
    if not ok:
        return msg

    pois = _gather_pois(lat, lng)

    buildings = [
        p for p in pois
        if any(k in p.get("place_name", "") for k in ["학교", "청", "구청", "시청", "센터"])
    ]

    if not buildings:
        return "반경 약 800미터 이내에 주요 건물이 없습니다."

    best = max(buildings, key=lambda x: x["_score"])
    return f"{best['place_name']}이 약 {int(best['_distance'])}미터 앞에 있습니다."


# ======================
# ✅ 시설 검색
# ======================

def get_nearest_facility(lat: float, lng: float, category_code: str) -> str:
    ok, msg = _validate_coords(lat, lng)
    if not ok:
        return msg

    if category_code not in CATEGORIES:
        return "지원하지 않는 시설입니다."

    pois, radius = _search_category(category_code, lat, lng)
    valid = []

    for p in pois:
        s = _score_poi(p, lat, lng, PRIORITY.get(category_code, PRIORITY["DEFAULT"]))
        if s: valid.append(s)

    if not valid:
        return f"반경 약 {radius}미터 이내에 {CATEGORIES[category_code]}이(가) 없습니다."

    best = max(valid, key=lambda x: x["_score"])
    return f"{best['place_name']}이 약 {int(best['_distance'])}미터 거리에 있습니다."
