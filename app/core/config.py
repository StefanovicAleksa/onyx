import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """
    Global Application Settings.
    Optimized for RTX 3060 (12GB VRAM).
    """
    # Project Root
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    
    # Logging
    LOG_LEVEL: str = "INFO"

    # --- Feature: Audio Extraction ---
    FFMPEG_BINARY_PATH: str | None = "ffmpeg" 
    DEFAULT_AUDIO_FORMAT: str = "mp3"
    FFMPEG_AUDIO_QUALITY_FLAGS: list[str] = ["-q:a", "0"]

    # --- Feature: Transcription ---
    WHISPER_MODEL_NAME: str = "large-v3"
    WHISPER_DEVICE: str = "cuda"

    # --- Feature: Intelligence Router ---
    # UPGRADE: Switched from 1.5B to 7B for smarter filtering.
    ROUTER_LLM_MODEL: str = "Qwen/Qwen2.5-7B-Instruct"
    ROUTER_DEVICE: str = "cuda"

    # --- Feature: Vision Analysis ---
    VISION_MODEL_NAME: str = "Qwen/Qwen2-VL-7B-Instruct"
    VISION_DEVICE: str = "cuda"

    # --- Feature: Knowledge Base (RAG) ---
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_DEVICE: str = "cuda"
    CHROMA_DB_PATH: Path = BASE_DIR / "data" / "chroma_db"

    # --- Feature: Chat / Inference ---
    CHAT_MODEL_NAME: str = "Qwen/Qwen2.5-14B-Instruct"
    CHAT_DEVICE: str = "cuda"

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Singleton instance
settings = Settings()