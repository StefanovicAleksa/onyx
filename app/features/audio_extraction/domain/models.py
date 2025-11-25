from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class AudioExtractionJob:
    """
    Represents a request to extract audio from a video file.
    
    Attributes:
        video_file_path (Path): The absolute path to the source video.
        output_audio_path (Path): The absolute path where the audio should be saved.
        quality_flags (list[str]): FFmpeg specific flags for audio quality.
        
    Note: This class is frozen (immutable) to ensure thread safety and 
    prevent side-effects during processing.
    """
    video_file_path: Path
    output_audio_path: Path
    quality_flags: list[str]