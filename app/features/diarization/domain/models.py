# File: app/features/diarization/domain/models.py
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass(frozen=True)
class SpeakerSegment:
    """
    A time range assigned to a specific speaker label.
    """
    start: float
    end: float
    speaker_label: str  # e.g., "speaker_0", "speaker_1"
    confidence: float = 0.0

@dataclass(frozen=True)
class DiarizationResult:
    """
    The output of the NeMo MSD (Multi-Scale Diarization) engine.
    """
    source_file: str
    num_speakers: int
    segments: List[SpeakerSegment] = field(default_factory=list)