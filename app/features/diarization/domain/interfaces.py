from abc import ABC, abstractmethod
from pathlib import Path
from .models import DiarizationResult

class IDiarizer(ABC):
    @abstractmethod
    def identify_speakers(self, audio_path: Path, num_speakers: int = None) -> DiarizationResult:
        """
        Analyzes audio to identify unique speakers.
        Args:
            audio_path: Path to wav/mp3.
            num_speakers: Optional hint if known (e.g., 2 for phone call).
        """
        pass