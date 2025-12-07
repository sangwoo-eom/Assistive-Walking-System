# core/env_risk.py

from typing import Dict, Iterable, List, Optional

# 위험 / 안전 구역 정의 (순서를 보장하기 위해 set 대신 tuple 사용)
DANGER_ZONES: Iterable[str] = ("roadway", "caution_zone")
SAFE_ZONES: Iterable[str] = ("sidewalk", "braille_guide_blocks")


def compute_env_risk(env_result: Optional[Dict[str, float]]) -> Dict[str, object]:
    """
    env_result 예:
    {
        "roadway_ratio": 0.45,
        "sidewalk_ratio": 0.32,
        "braille_guide_blocks_ratio": 0.08,
        "caution_zone_ratio": 0.12
    }

    반환:
    {
        "danger_zones": [ ... ],
        "safe_zones": [ ... ],
        "current_zone": "roadway" | "sidewalk" | ... | None,
        "is_danger": True/False
    }
    """
    if env_result is None:
        env_result = {}

    danger: List[str] = []
    safe: List[str] = []

    # --------- 위험 구역 검사 ---------
    for zone in DANGER_ZONES:
        ratio = float(env_result.get(f"{zone}_ratio", 0.0))
        if ratio > 0.25:   # TODO: 현장 테스트 후 조정
            danger.append(zone)

    # --------- 안전 구역 검사 ---------
    for zone in SAFE_ZONES:
        ratio = float(env_result.get(f"{zone}_ratio", 0.0))
        if ratio > 0.15:
            safe.append(zone)

    # --------- 현재 주 구역 추론 ---------
    current_zone: Optional[str] = None
    if danger:
        # 위험 구역이 여러 개라면, 비율이 가장 큰 것을 선택
        current_zone = max(
            danger,
            key=lambda z: float(env_result.get(f"{z}_ratio", 0.0))
        )
    elif safe:
        # 위험 구역이 없고, 안전 구역만 있다면 그 중 비율이 가장 큰 것
        current_zone = max(
            safe,
            key=lambda z: float(env_result.get(f"{z}_ratio", 0.0))
        )

    return {
        "danger_zones": danger,
        "safe_zones": safe,
        "current_zone": current_zone,
        "is_danger": bool(danger),
    }
