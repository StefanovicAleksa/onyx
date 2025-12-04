import os
import shutil
from pathlib import Path

class Config:
    """
    Global Application Configuration.
    Handles environment variables and system path resolution.
    """
    # 1. FFmpeg Binary Resolution
    # Priority: Env Var -> System Path -> Default "ffmpeg"
    FFMPEG_BINARY: str = os.getenv("FFMPEG_BINARY_PATH", shutil.which("ffmpeg") or "ffmpeg")
    
    # 2. Project Base Directory (Absolute Path)
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent

# Singleton Instance
settings = Config()