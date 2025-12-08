import os
import shutil
from pathlib import Path

class Config:
    # 1. Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    ARTIFACTS_DIR: Path = DATA_DIR / "artifacts"
    
    # 2. Database (PostgreSQL)
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "password")
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "onyx_db")
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # 3. FFmpeg
    FFMPEG_BINARY: str = os.getenv("FFMPEG_BINARY_PATH", shutil.which("ffmpeg") or "ffmpeg")
    
    # 4. Transcription Settings
    WHISPER_MODEL_NAME: str = os.getenv("WHISPER_MODEL_NAME", "large-v3")
    WHISPER_DEVICE: str = "cuda"

    def ensure_dirs(self):
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

settings = Config()
