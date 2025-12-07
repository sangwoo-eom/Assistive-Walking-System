# core/config.py

from pathlib import Path
from typing import ClassVar, Set
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    프로젝트 전역 설정 관리
    """

    # ===========================
    # 프로젝트 루트
    # ===========================
    BASE_DIR: Path = Path(__file__).resolve().parent.parent

    # ===========================
    # 모델 가중치 경로
    # ===========================
    OBJECT_DETECTOR_WEIGHTS: Path = BASE_DIR / "weights" / "object_detector.pt"
    ENV_SEGMENTER_WEIGHTS: Path = BASE_DIR / "weights" / "env_segmenter.pt"

    # ===========================
    # 디바이스 설정
    # ===========================
    DEVICE: str = "cuda"   # "cuda" or "cpu"

    # ===========================
    # 업로드 디렉토리
    # ===========================
    UPLOAD_DIR: Path = BASE_DIR / "uploads"

    # ===========================
    # 서버 설정
    # ===========================
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000

    # ===========================
    # 업로드 제한
    # ===========================
    MAX_IMAGE_SIZE_MB: int = 10
    ALLOW_EXTENSIONS: ClassVar[Set[str]] = {"jpg", "jpeg", "png"}

    # ===========================
    # Kakao Local API 설정
    # ===========================
    KAKAO_REST_API_KEY: str = ""   # 반드시 .env에 설정

    # ===========================
    # Pydantic Config
    # ===========================
    class Config:
        env_file = ".env"
        case_sensitive = True

    # ===========================
    # 디렉토리 보장
    # ===========================
    def ensure_directories(self):
        """ 필수 디렉토리 생성 """
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# 전역 설정 로드
settings = Settings()
settings.ensure_directories()
