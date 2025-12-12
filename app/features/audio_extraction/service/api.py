from pathlib import Path
from ..domain.models import ExtractionConfig, ExtractionResult
from ..data.ffmpeg_adapter import FFmpegAdapter

def run_extraction(video_path: str, output_dir: str) -> ExtractionResult:
    """
    Standalone API: Extracts audio from a video file.
    Does NOT interact with the database.
    """
    adapter = FFmpegAdapter()
    config = ExtractionConfig() # Uses defaults
    
    return adapter.extract_audio(Path(video_path), Path(output_dir), config)