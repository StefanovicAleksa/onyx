from dataclasses import dataclass, field
from typing import List
from app.core.shared_types import MediaFile

@dataclass(frozen=True)
class TranscriptionSegment:
    """
    A single piece of transcribed text with precise timing.
    Critical for the 'Intelligence Router' to know WHEN a topic was discussed.
    """
    start_time: float
    end_time: float
    text: str

@dataclass(frozen=True)
class TranscriptionResult:
    """
    The complete result of a transcription job.
    """
    source_audio: MediaFile
    language: str
    full_text: str
    segments: List[TranscriptionSegment] = field(default_factory=list)
    model_used: str = "unknown"