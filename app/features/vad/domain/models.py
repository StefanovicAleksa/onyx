# File: app/features/vad/domain/models.py
from dataclasses import dataclass
from enum import Enum

class VadEventType(str, Enum):
    SPEECH = "speech"
    SILENCE = "silence"

@dataclass(frozen=True)
class VadSegment:
    """
    A period of activity or silence.
    """
    start: float
    end: float
    event_type: VadEventType
    confidence: float