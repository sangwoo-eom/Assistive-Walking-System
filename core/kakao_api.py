import logging
import requests
from typing import Dict, Any

from core.config import settings

logger = logging.getLogger(__name__)

KAKAO_REST_API_KEY = getattr(settings, "KAKAO_REST_API_KEY", "")
BASE_URL = "https://dapi.kakao.com/v2/local"

HEADERS = {
    "Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"
}


def _kakao_get(path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Kakao Local API GET 요청"""
    if not KAKAO_REST_API_KEY:
        logger.warning("[kakao_api] KAKAO_REST_API_KEY 미설정")
        return {}

    url = f"{BASE_URL}{path}"
    try:
        res = requests.get(url, headers=HEADERS, params=params, timeout=2.5)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        logger.error(f"[kakao_api] API 요청 실패: {e}")
        return {}


def coord2address(lat: float, lng: float) -> Dict[str, Any]:
    """좌표 → 주소 변환"""
    return _kakao_get(
        "/geo/coord2address.json",
        {"x": lng, "y": lat, "input_coord": "WGS84"}
    )


def search_category(
    category_code: str,
    lat: float,
    lng: float,
    radius: int = 200,
    size: int = 15
) -> Dict[str, Any]:
    """카테고리 기반 장소 검색"""
    return _kakao_get(
        "/search/category.json",
        {
            "category_group_code": category_code,
            "x": lng,
            "y": lat,
            "radius": radius,
            "size": size,
            "sort": "distance",
        }
    )


def search_keyword(
    query: str,
    lat: float,
    lng: float,
    radius: int = 200,
    size: int = 10
) -> Dict[str, Any]:
    """키워드 기반 장소 검색"""
    return _kakao_get(
        "/search/keyword.json",
        {
            "query": query,
            "x": lng,
            "y": lat,
            "radius": radius,
            "size": size,
            "sort": "distance",
        }
    )
