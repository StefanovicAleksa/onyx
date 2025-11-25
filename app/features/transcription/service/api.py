from pathlib import Path
import logging
from app.core.config import settings
from ..domain.models import TranscriptionJob, TranscriptionResult
from ..data.whisper_transcriber import WhisperTranscriber

logger = logging.getLogger(__name__)

def transcribe_audio(audio_path: Path | str) -> TranscriptionResult:
    """
    Main Entrypoint: Transcribes an audio file to text.
    
    Args:
        audio_path: Path to the source audio file (mp3, wav, m4a).
                     
    Returns:
        TranscriptionResult object containing text and metadata.
    """
    audio_path_obj = Path(audio_path)
    
    # Dependency Injection
    # NOTE: We instantiate the Transcriber here. 
    # In production, the 'Orchestrator' will manage this instance 
    # to prevent reloading the model (and hitting VRAM limits) repeatedly.
    transcriber = WhisperTranscriber()
    
    job = TranscriptionJob(
        audio_file_path=audio_path_obj
    )

    return transcriber.transcribe(job)