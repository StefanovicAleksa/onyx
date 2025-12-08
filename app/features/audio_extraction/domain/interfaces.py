from abc import ABC, abstractmethod
from .models import AudioExtractionTask

class IAudioExtractor(ABC):
    """
    Interface (Contract) for the audio extraction implementation.
    """
    
    @abstractmethod
    def extract(self, task: AudioExtractionTask) -> None:
        """
        Executes the extraction task.
        """
        pass
