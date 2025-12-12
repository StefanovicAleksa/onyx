from abc import ABC, abstractmethod
from .models import TranscriptionResult

class ITranscriber(ABC):
    """
    Contract for any ASR (Automatic Speech Recognition) engine.
    Allows us to swap Whisper for Faster-Whisper or API-based solutions later.
    """
    @abstractmethod
    def transcribe(self, audio_path: str, model_size: str) -> TranscriptionResult:
        """
        Transcribes the audio file at the given path.
        
        Args:
            audio_path: Absolute path to the audio file.
            model_size: 'tiny', 'base', 'small', 'medium', 'large-v3'.
            
        Returns:
            Structured TranscriptionResult.
        """
        pass