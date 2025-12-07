# routes/stt.py

from fastapi import APIRouter, UploadFile, File, HTTPException
from core.stt import transcribe_audio_file

router = APIRouter()

@router.post("/stt")
async def stt_endpoint(file: UploadFile = File(...)):
    """
    브라우저에서 넘어온 짧은 음성을 Whisper로 인식하고
    intent/원문 텍스트를 함께 반환한다.
    """
    try:
        audio_bytes = await file.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="빈 오디오입니다.")

        result = transcribe_audio_file(audio_bytes, suffix=".webm")
        # result: {"intent": "...", "raw": "...", "norm": "..."}
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"STT 실패: {e}")
