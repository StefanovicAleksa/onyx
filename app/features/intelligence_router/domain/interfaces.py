from abc import ABC, abstractmethod
from app.features.transcription.domain.models import TranscriptionResult
from .models import RoutingResult

class IIntelligenceRouter(ABC):
    """
    Interface for the Router.
    Decouples the implementation (LLM vs Embeddings) from the usage.
    """
    
    @abstractmethod
    def route(self, transcript: TranscriptionResult) -> RoutingResult:
        """
        Analyzes the transcript and extracts visual queries.
        
        Args:
            transcript: The output from the Transcription feature.
            
        Returns:
            RoutingResult: A list of timestamps and queries.
        """
        pass