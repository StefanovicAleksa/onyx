# File: app/features/transcription/domain/models.py
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass(frozen=True)
class WordTiming:
    """
    Atomic unit of a spoken word for 'Karaoke' style playback.
    """
    word: str
    start: float
    end: float
    confidence: float

@dataclass(frozen=True)
class TranscriptionSegment:
    """
    Represents a specific phrase with exact timing and rich metadata.
    """
    start: float
    end: float
    text: str
    confidence: float = 0.0
    
    # Placeholder for the future Pipeline to populate
    speaker_id: Optional[str] = None 
    
    # Rich Metadata
    words: List[WordTiming] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict) # Catch-all for VAD gaps, noise flags, etc.

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
    
    # Header Metadata
    duration_seconds: float = 0.0
    processing_meta: Dict[str, Any] = field(default_factory=dict)