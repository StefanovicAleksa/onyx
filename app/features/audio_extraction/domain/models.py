from dataclasses import dataclass
from app.core.shared_types import MediaFile

@dataclass(frozen=True)
class AudioExtractionJob:
    """
    Domain entity describing the intent to extract audio from a video.
    """
    source_video: MediaFile
    output_audio: MediaFile
    bitrate_kbps: int = 192  # Default high-quality bitrate