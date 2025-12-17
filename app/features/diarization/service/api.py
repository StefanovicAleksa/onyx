# File: app/features/diarization/service/api.py
from typing import Optional
from ..data.nemo_adapter import NemoDiarizationAdapter
from ..domain.models import DiarizationResult

def run_diarization(audio_path: str, num_speakers: Optional[int] = None) -> DiarizationResult:
    """
    Public API for the Diarization Feature.
    Used by the Pipeline to enrich transcripts.
    """
    adapter = NemoDiarizationAdapter()
    return adapter.run_inference(audio_path, num_speakers)