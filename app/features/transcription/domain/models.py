from dataclasses import dataclass, field
from typing import List, Optional

@dataclass(frozen=True)
class TranscriptionSegment:
    """
    Represents a specific phrase with exact timing.
    This is the atomic unit for RAG retrieval later.
    """
    start: float
    end: float
    text: str
    confidence: float = 0.0

@dataclass(frozen=True)
class TranscriptionResult:
    """
    The complete output of the ASR engine.
    """
    source_file: str
    language: str
    model_used: str
    full_text: str
    segments: List[TranscriptionSegment] = field(default_factory=list)