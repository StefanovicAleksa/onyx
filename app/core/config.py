# File: app/core/config_v2.py
import shutil
import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """
    Global Application Settings.
    Updated for RTX 3060 (12GB VRAM) Production Environment.
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
    # UPGRADE: 'medium' -> 'large-v3'. 
    # The 3060 can handle the ~3GB VRAM requirement easily.
    # significantly better for medical/legal terminology.
    WHISPER_MODEL_NAME: str = "large-v3"
    WHISPER_DEVICE: str = "cuda"

    # --- Feature: Intelligence Router ---
    ROUTER_LLM_MODEL: str = "Qwen/Qwen2.5-1.5B-Instruct"
    ROUTER_DEVICE: str = "cuda"

    # --- Feature: Vision Analysis ---
    # UPGRADE: Enabled Option B (7B Model).
    # 4-bit Quantization (implemented in code) brings this to ~5.5GB VRAM.
    VISION_MODEL_NAME: str = "Qwen/Qwen2-VL-7B-Instruct"
    VISION_DEVICE: str = "cuda"

    # --- Feature: Knowledge Base (RAG) ---
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-small-en-v1.5"
    
    # OPTIMIZATION: Move from 'cpu' to 'cuda'.
    # This model is tiny (~200MB). With 12GB, we can afford to keep it 
    # loaded on the GPU for lightning-fast indexing and retrieval.
    EMBEDDING_DEVICE: str = "cuda" 
    
    CHROMA_DB_PATH: Path = BASE_DIR / "data" / "chroma_db"

    # --- Feature: Chat / Inference ---
    # UPGRADE: Enabled Option B (14B Model).
    # 4-bit Quantization brings this to ~9GB VRAM.
    # It fits in the 12GB buffer *provided* we unload Vision/Whisper first.
    CHAT_MODEL_NAME: str = "Qwen/Qwen2.5-14B-Instruct"
    CHAT_DEVICE: str = "cuda"

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Singleton instance
settings = Settings()