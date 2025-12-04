from abc import ABC, abstractmethod
from app.core.shared_types import MediaFile
from .models import TranscriptionResult

class ITranscriber(ABC):
    """
    Interface (Contract) for the transcription engine.
    """
    
    @abstractmethod
    def transcribe(self, audio_file: MediaFile) -> TranscriptionResult:
        """
        Transcribes the given audio file into text with timestamps.
        
        Args:
            audio_file: The source audio.
            
        Returns:
            TranscriptionResult containing segments and full text.
            
        Raises:
            FileNotFoundError, RuntimeError
        """
        pass