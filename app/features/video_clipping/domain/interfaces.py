from abc import ABC, abstractmethod
from .models import ClipRequest

class IClipGenerator(ABC):
    """
    Contract for the video clipping engine.
    Abstracts away the underlying tool (FFmpeg) from the business logic.
    """
    
    @abstractmethod
    def create_clip(self, request: ClipRequest) -> None:
        """
        Generates a sub-clip from the source video based on the request parameters.
        
        Args:
            request: The ClipRequest entity containing source, output, and timestamps.
            
        Raises:
            FileNotFoundError: If source does not exist.
            RuntimeError: If the underlying clipping process fails.
        """
        pass