# routes/stt.py

from fastapi import APIRouter, UploadFile, File, HTTPException
from core.stt import transcribe_audio_file

router = APIRouter()


@router.post("/stt")
async def stt_endpoint(file: UploadFile = File(...)):
    """
    업로드된 짧은 음성 파일을 STT 모델로 변환하여
    인식 결과를 반환한다.

    반환 형식:
    {
        "intent": "...",
        "raw": "...",
        "norm": "..."
    }
    """
    try:
        audio_bytes = await file.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio file.")

        result = transcribe_audio_file(audio_bytes, suffix=".webm")
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"STT error: {e}")
