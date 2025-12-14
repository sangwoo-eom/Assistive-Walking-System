from typing import Dict, Iterable, List, Optional

# 환경 분류 기준
DANGER_ZONES: Iterable[str] = ("roadway", "caution_zone")
SAFE_ZONES: Iterable[str] = ("sidewalk", "braille_guide_blocks")


def compute_env_risk(env_result: Optional[Dict[str, float]]) -> Dict[str, object]:
    """
    환경 분할 결과를 기반으로 위험 여부 판단
    """
    if env_result is None:
        env_result = {}

    danger: List[str] = []
    safe: List[str] = []

    # 위험 구역 판별
    for zone in DANGER_ZONES:
        ratio = float(env_result.get(f"{zone}_ratio", 0.0))
        if ratio > 0.25:  # 현장 테스트 기준값
            danger.append(zone)

    # 안전 구역 판별
    for zone in SAFE_ZONES:
        ratio = float(env_result.get(f"{zone}_ratio", 0.0))
        if ratio > 0.15:
            safe.append(zone)

    # 주 영역 결정
    current_zone: Optional[str] = None
    if danger:
        current_zone = max(
            danger,
            key=lambda z: float(env_result.get(f"{z}_ratio", 0.0))
        )
    elif safe:
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
