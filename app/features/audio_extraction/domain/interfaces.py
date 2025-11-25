from abc import ABC, abstractmethod
from .models import AudioExtractionJob

class IAudioExtractor(ABC):
    """
    Abstract Base Class (Interface) for the Audio Extraction tool.
    
    This decouples the application logic from the specific implementation 
    (FFmpeg, GStreamer, MoviePy, etc.).
    """
    
    @abstractmethod
    def extract(self, job: AudioExtractionJob) -> None:
        """
        Runs the extraction process.
        
        Args:
            job (AudioExtractionJob): The job details containing paths and settings.
            
        Raises:
            RuntimeError: If the extraction process fails.
        """
        pass