# File: app/features/vad/service/api.py
from typing import List
from ..data.marblenet_adapter import MarbleNetAdapter
from ..domain.models import VadSegment

def run_vad_analysis(audio_path: str) -> List[VadSegment]:
    """
    Public API for Voice Activity Detection.
    """
    adapter = MarbleNetAdapter()
    return adapter.detect_voice(audio_path)