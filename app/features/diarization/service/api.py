from pathlib import Path
from ..data.nemo_adapter import NemoDiarizationAdapter
from ..domain.models import DiarizationResult

def run_diarization(audio_path: str) -> DiarizationResult:
    """
    Public Service API for Speaker Identification.
    """
    adapter = NemoDiarizationAdapter()
    return adapter.identify_speakers(Path(audio_path))