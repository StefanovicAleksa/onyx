import shutil
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    """
    Global Application Settings.
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
    WHISPER_MODEL_NAME: str = "small" 
    WHISPER_DEVICE: str = "cuda"

    # --- Feature: Intelligence Router ---
    ROUTER_LLM_MODEL: str = "Qwen/Qwen2.5-1.5B-Instruct"
    ROUTER_DEVICE: str = "cuda"

    # --- Feature: Vision Analysis (The Hardware Switch) ---
    
    # OPTION A: Current Hardware (GTX 1050 Ti - 4GB VRAM)
    # Uses ~1.5GB VRAM. Fast, efficient, good basic OCR.
    VISION_MODEL_NAME: str = "Qwen/Qwen2-VL-2B-Instruct"

    # OPTION B: Future Hardware (RTX 3060 - 12GB VRAM)
    # Uses ~5.5GB VRAM (4-bit). Massive intelligence upgrade.
    # Uncomment this line when you get the new card:
    # VISION_MODEL_NAME: str = "Qwen/Qwen2-VL-7B-Instruct"
    
    VISION_DEVICE: str = "cuda"

    # Modern Pydantic V2 Configuration
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Singleton instance
settings = Settings()