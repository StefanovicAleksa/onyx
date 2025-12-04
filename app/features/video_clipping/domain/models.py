from dataclasses import dataclass
from app.core.shared_types import MediaFile, TimeRange

@dataclass(frozen=True)
class ClipRequest:
    """
    Domain entity describing the intent to cut a specific segment from a video.
    """
    source_video: MediaFile
    output_video: MediaFile
    time_range: TimeRange