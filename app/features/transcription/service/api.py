from ..data.whisper_adapter import WhisperAdapter
from ..domain.models import TranscriptionResult

def run_transcription(audio_path: str, model_size: str = "large-v3") -> TranscriptionResult:
    """
    Standalone API for running transcription directly.
    Useful for testing or CLI tools without the full Job system.
    """
    adapter = WhisperAdapter()
    return adapter.transcribe(audio_path, model_size)