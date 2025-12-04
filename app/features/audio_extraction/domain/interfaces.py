from abc import ABC, abstractmethod
from .models import AudioExtractionJob

class IAudioExtractor(ABC):
    """
    Interface (Contract) for the audio extraction implementation.
    This strictly decouples the domain logic from the FFmpeg implementation.
    """
    
    @abstractmethod
    def extract(self, job: AudioExtractionJob) -> None:
        """
        Executes the extraction job.
        
        Args:
            job: The AudioExtractionJob containing source and destination paths.
            
        Raises:
            FileNotFoundError: If source video is missing.
            RuntimeError: If the underlying tool (FFmpeg) fails.
        """
        pass