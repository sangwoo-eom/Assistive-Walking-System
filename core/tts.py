# core/tts.py


# =======================
# 클래스 → 한국어 라벨
# =======================

TTS_CLASS_MAP = {
    "barricade": "장애물",
    "bench": "벤치",
    "bicycle": "자전거",
    "bollard": "기둥",
    "bus": "버스",
    "car": "차량",
    "carrier": "캐리어",
    "cat": "고양이",
    "chair": "의자",
    "dog": "개",
    "fire_hydrant": "소화전",
    "kiosk": "키오스크",
    "motorcycle": "오토바이",
    "movable_signage": "이동식 표지판",
    "parking_meter": "주차 요금기",
    "person": "사람",
    "pole": "기둥",
    "potted_plant": "화분",
    "power_controller": "전기 제어함",
    "scooter": "스쿠터",
    "stop": "정지 표지판",
    "stroller": "유모차",
    "table": "탁자",
    "traffic_light": "신호등",
    "traffic_light_controller": "신호 제어기",
    "traffic_sign": "교통 표지판",
    "tree_trunk": "나무 기둥",
    "truck": "트럭",
    "wheelchair": "휠체어",
}


# =======================
# 조사 붙이기
# =======================

def add_particle(word: str) -> str:
    """
    종성 유무에 따라 조사 '이/가' 자동 선택
    """
    if not word:
        return word

    last_char = word[-1]
    code = ord(last_char) - 0xAC00

    if code < 0 or code > 11171:
        return word + "이"

    jong = code % 28
    return word + ("이" if jong != 0 else "가")


# =======================
# 방향 계산
# =======================

def get_direction(center_x: float, frame_w: int) -> str:
    """
    bbox 중심 x좌표 기준으로 방향 구분
    """
    if frame_w <= 0:
        return "정면"

    ratio = center_x / frame_w

    if ratio < 1 / 3:
        return "왼쪽"
    elif ratio > 2 / 3:
        return "오른쪽"
    else:
        return "정면"


# =======================
# 경고 문장 생성
# =======================

def build_warning_message(cls_name: str, center_x: float, frame_w: int) -> str:
    """
    예:
    "왼쪽에서 차량이 다가오고 있습니다."
    """
    # 라벨 변환
    label = TTS_CLASS_MAP.get(cls_name, "물체")

    # 조사 추가
    label = add_particle(label)

    # 방향 계산
    direction = get_direction(center_x, frame_w)

    # 최종 문장
    return f"{direction}에서 {label} 다가오고 있습니다."
