from abc import ABC, abstractmethod
from .models import ClipRequest

class IClipGenerator(ABC):
    """
    Interface (Contract) for the video clipping implementation.
    """
    
    @abstractmethod
    def create_clip(self, request: ClipRequest) -> None:
        """
        Creates a sub-clip based on the request parameters.
        
        Args:
            request: The ClipRequest containing source, output, and timestamps.
            
        Raises:
            FileNotFoundError, RuntimeError
        """
        pass