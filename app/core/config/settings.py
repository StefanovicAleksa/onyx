# File: app/core/config/settings.py

import os
import shutil
from pathlib import Path


class Settings:
    # --- Paths ---
    # app/core/config/settings.py -> app/core/config -> app/core -> app -> ROOT
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    ARTIFACTS_DIR: Path = DATA_DIR / "artifacts"
    MODELS_DIR: Path = BASE_DIR / "models"

    # --- Database ---
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "password")
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "onyx_db")

    @property
    def DATABASE_URL(self) -> str:
        # ARCHITECTURAL FIX:
        # Only fallback to SQLite if explicitly requested.
        # Otherwise, default to the Docker Postgres (even in TEST_MODE).
        if os.getenv("USE_SQLITE", "false").lower() == "true":
            return "sqlite:///./test_onyx.db"

        # Default: Use the Docker Postgres instance
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # --- External Tools ---
    # Auto-detect ffmpeg or use env var
    FFMPEG_BINARY: str = os.getenv("FFMPEG_BINARY_PATH", shutil.which("ffmpeg") or "ffmpeg")

    # --- Model Configuration ---
    WHISPER_MODEL_NAME: str = "large-v3"
    WHISPER_DEVICE: str = "cuda" if os.getenv("USE_CUDA", "true").lower() == "true" else "cpu"

    # --- NeMo Model Paths ---
    NEMO_VAD_PATH: Path = MODELS_DIR / "nemo/vad_multilingual_marblenet.nemo"
    NEMO_DIAR_PATH: Path = MODELS_DIR / "nemo/titanet_large.nemo"

    def ensure_dirs(self):
        """Creates necessary data directories if they don't exist."""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        self.MODELS_DIR.mkdir(parents=True, exist_ok=True)
        (self.MODELS_DIR / "nemo").mkdir(parents=True, exist_ok=True)


settings = Settings()