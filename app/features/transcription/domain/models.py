from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any

@dataclass(frozen=True)
class TranscriptionJob:
    audio_file_path: Path
    language: str | None = None

@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    language: str
    processing_time: float
    segments: List[Dict[str, Any]] = field(default_factory=list)