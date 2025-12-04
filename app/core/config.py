import os
import shutil
from pathlib import Path

class Config:
    """
    Global Application Configuration.
    """
    # 1. Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    
    # 2. FFmpeg
    FFMPEG_BINARY: str = os.getenv("FFMPEG_BINARY_PATH", shutil.which("ffmpeg") or "ffmpeg")
    
    # 3. Transcription Settings
    # This was missing in your previous version, causing the AttributeError
    WHISPER_MODEL_NAME: str = os.getenv("WHISPER_MODEL_NAME", "large-v3")
    WHISPER_DEVICE: str = "cuda" # We assume GPU for the appliance

# Singleton Instance
settings = Config()