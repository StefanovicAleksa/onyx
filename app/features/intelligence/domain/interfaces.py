from abc import ABC, abstractmethod
from typing import List
from .models import IntelligenceInsight


class ILLMAdapter(ABC):
    """
    Interface for Local LLM interaction.
    The Core Orchestrator will call load/unload.
    The Intelligence Service will call analyze.
    """

    @abstractmethod
    def load(self):
        """Load model into VRAM (called by Core)."""
        pass

    @abstractmethod
    def unload(self):
        """Clear VRAM (called by Core)."""
        pass

    @abstractmethod
    def analyze_text(self, text: str) -> List[IntelligenceInsight]:
        """Process a script segment and return structured insights."""
        pass