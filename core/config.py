from pathlib import Path
from typing import ClassVar, Set
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    프로젝트 전역 설정
    """

    # 프로젝트 루트 경로
    BASE_DIR: Path = Path(__file__).resolve().parent.parent

    # 모델 가중치 경로
    OBJECT_DETECTOR_WEIGHTS: Path = BASE_DIR / "weights" / "object_detector.pt"
    ENV_SEGMENTER_WEIGHTS: Path = BASE_DIR / "weights" / "env_segmenter.pt"

    # 실행 디바이스 ("cuda" or "cpu")
    DEVICE: str = "cuda"

    # 업로드 파일 저장 경로
    UPLOAD_DIR: Path = BASE_DIR / "uploads"

    # 서버 설정
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000

    # 업로드 제한
    MAX_IMAGE_SIZE_MB: int = 10
    ALLOW_EXTENSIONS: ClassVar[Set[str]] = {"jpg", "jpeg", "png"}

    # Kakao Local API
    KAKAO_REST_API_KEY: str = ""  # .env 파일에서 로드

    class Config:
        env_file = ".env"
        case_sensitive = True

    def ensure_directories(self):
        """필수 디렉토리 생성"""
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# 전역 설정 인스턴스
settings = Settings()
settings.ensure_directories()
