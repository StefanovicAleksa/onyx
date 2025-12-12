from pathlib import Path
from typing import List
from ..domain.models import SpeechSegment
from ..data.marblenet_adapter import MarblenetAdapter

def detect_voice_activity(audio_path: str) -> List[SpeechSegment]:
    """
    Public API: Detects speech segments in an audio file.
    Uses GPU acceleration via Core Orchestrator.
    """
    adapter = MarblenetAdapter()
    return adapter.detect_speech(Path(audio_path))