from abc import ABC, abstractmethod
from .models import TranscriptionJob, TranscriptionResult

class ITranscriber(ABC):
    """
    Interface for the Transcription engine.
    Decouples the app from OpenAI Whisper.
    """
    
    @abstractmethod
    def transcribe(self, job: TranscriptionJob) -> TranscriptionResult:
        """
        Transcribes the audio file.
        
        Args:
            job (TranscriptionJob): The job details.
            
        Returns:
            TranscriptionResult: The text and metadata.

        Raises:
            RuntimeError: If transcription fails.
        """
        pass