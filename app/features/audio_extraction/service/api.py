from pathlib import Path
import logging
from app.core.config import settings
from ..domain.models import AudioExtractionJob
from ..data.ffmpeg_extractor import FFmpegAudioExtractor

logger = logging.getLogger(__name__)

def extract_audio(video_path: Path | str, output_path: Path | str | None = None) -> Path:
    """
    Main Entrypoint: Extracts audio from a video file.
    
    This function acts as the Facade for the Audio Extraction feature.
    It handles:
    1. Path validation.
    2. Determining default output paths.
    3. Dependency Injection (instantiating the FFmpeg extractor).
    
    Args:
        video_path: Path to source video.
        output_path: Optional path for destination audio. 
                     Defaults to same name as video with .mp3 extension.
                     
    Returns:
        Path object to the generated audio file.
    """
    video_path_obj = Path(video_path)
    
    # 1. Validation
    if not video_path_obj.exists():
        logger.error(f"Video file not found: {video_path_obj}")
        raise FileNotFoundError(f"Video file not found: {video_path}")

    # 2. Default Logic
    if output_path:
        output_path_obj = Path(output_path)
    else:
        output_path_obj = video_path_obj.with_suffix(f".{settings.DEFAULT_AUDIO_FORMAT}")

    # 3. Dependency Injection
    # In a larger app, this might come from a DI container.
    extractor = FFmpegAudioExtractor()
    
    job = AudioExtractionJob(
        video_file_path=video_path_obj,
        output_audio_path=output_path_obj,
        quality_flags=settings.FFMPEG_AUDIO_QUALITY_FLAGS
    )

    logger.info(f"Starting audio extraction job for: {video_path_obj.name}")
    
    try:
        extractor.extract(job)
        logger.info(f"Audio extraction complete: {output_path_obj}")
        return output_path_obj
    except Exception as e:
        logger.error(f"Audio Extraction Service failed: {e}")
        raise