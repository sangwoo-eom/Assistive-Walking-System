import tempfile
import os
import torch
import whisper

_model = None


def get_whisper_model():
    global _model
    if _model is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _model = whisper.load_model("base", device=device)
    return _model


def _normalize_text(text: str) -> str:
    t = text.strip().lower().replace(" ", "")

    junk_words = [
        "좀", "조금", "약간", "그냥", "이제", "지금", "요", "요?", "요.",
        "거야", "거지", "인가요", "인가요?", "인가",
        "해주세요", "해줘", "해주세요요", "좀요",
    ]

    for j in junk_words:
        t = t.replace(j, "")

    return t


def normalize_command(text: str) -> dict:
    norm = _normalize_text(text)

    def has(*words):
        return any(w in norm for w in words)

    if has("시작", "실행", "가동", "켜"):
        return {"intent": "system_start", "raw": text, "norm": norm}

    if has("종료", "끝내", "꺼", "중지", "멈춰"):
        return {"intent": "system_stop", "raw": text, "norm": norm}

    if has("객체", "물체", "뭐있어", "위험한거", "위험한게", "주변뭐", "사람있어", "차있어"):
        return {"intent": "object_guide", "raw": text, "norm": norm}

    if has("위험환경", "위험한곳", "위험해", "조심", "조심할"):
        return {"intent": "env_danger", "raw": text, "norm": norm}

    if has("안전환경", "안전해", "안전한곳"):
        return {"intent": "env_safe", "raw": text, "norm": norm}

    if has("환경안내", "환경메뉴", "주변환경"):
        return {"intent": "env_menu", "raw": text, "norm": norm}

    if has("경고꺼", "경고그만", "조용히", "그만말해", "알람꺼", "mute"):
        return {"intent": "env_alert_off", "raw": text, "norm": norm}

    if has("경고켜", "알람켜", "다시알려줘", "다시경고", "경고재개"):
        return {"intent": "env_alert_on", "raw": text, "norm": norm}

    if has("위치메뉴", "위치안내"):
        return {"intent": "location_menu", "raw": text, "norm": norm}

    if has("여기어디", "지금어디", "내위치", "현재위치"):
        return {"intent": "location_summary", "raw": text, "norm": norm}

    if has("주소", "지번"):
        return {"intent": "location_address", "raw": text, "norm": norm}

    if has("주변건물", "건물", "무슨건물"):
        return {"intent": "location_landmark", "raw": text, "norm": norm}

    if has("편의시설", "생활시설", "시설", "병원", "약국", "마트", "편의점", "지하철", "역"):
        return {"intent": "location_facility", "raw": text, "norm": norm}

    if has("천천히", "느리게"):
        return {"intent": "tts_slow", "raw": text, "norm": norm}

    if has("빨리", "빠르게"):
        return {"intent": "tts_fast", "raw": text, "norm": norm}

    if has("보통속도", "기본속도", "원래대로"):
        return {"intent": "tts_normal", "raw": text, "norm": norm}

    if has("뒤로", "뒤로가기", "메인", "처음"):
        return {"intent": "ui_back", "raw": text, "norm": norm}

    if has("사진", "이미지", "찍어", "분석"):
        return {"intent": "upload_image", "raw": text, "norm": norm}

    if has("다시말해", "다시", "한번더"):
        return {"intent": "repeat_last", "raw": text, "norm": norm}

    return {"intent": "unknown", "raw": text, "norm": norm}


def transcribe_audio_file(file_bytes: bytes, suffix: str = ".webm") -> dict:
    model = get_whisper_model()

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
        f.write(file_bytes)
        temp_path = f.name

    try:
        result = model.transcribe(temp_path, language="ko")
        text = (result.get("text") or "").strip()
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass

    if not text:
        return {"intent": "unknown", "raw": "", "norm": ""}

    return normalize_command(text)
