from dataclasses import dataclass
from pathlib import Path
from app.core.shared_types import MediaFile

@dataclass(frozen=True)
class AudioExtractionTask:
    source_video: MediaFile
    output_audio: MediaFile
    bitrate_kbps: int = 192
    def __post_init__(self):
        if not self.source_video.exists(): raise FileNotFoundError(f"Missing video: {self.source_video.path}")
