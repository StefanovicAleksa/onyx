from pathlib import Path
from app.core.shared_types import MediaFile
from ..domain.models import TranscriptionResult
from ..data.whisper_adapter import WhisperAdapter

def transcribe_audio(audio_path: str, model_size: str = "large-v3") -> TranscriptionResult:
    """
    Public Service API: Transcribes an audio file locally.
    
    Args:
        audio_path: Path to the audio file (mp3, wav).
        model_size: Whisper model size (tiny, base, small, medium, large-v3).
                    Defaults to 'large-v3' for maximum accuracy.
    """
    # 1. Map to Domain
    source = MediaFile(Path(audio_path))
    
    # 2. Instantiate Adapter
    # Note: In a production app, we would manage the lifecycle of this adapter 
    # carefully to avoid keeping 3GB in VRAM when not in use.
    adapter = WhisperAdapter(model_size=model_size)
    
    # 3. Execute
    return adapter.transcribe(source)