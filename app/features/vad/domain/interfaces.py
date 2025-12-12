from abc import ABC, abstractmethod
from typing import List
from pathlib import Path
from .models import SpeechSegment

class IVoiceActivityDetector(ABC):
    @abstractmethod
    def detect_speech(self, audio_path: Path) -> List[SpeechSegment]:
        """
        Scans audio and returns a list of segments containing human speech.
        """
        pass