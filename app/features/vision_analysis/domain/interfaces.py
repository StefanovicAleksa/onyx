from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Any
from .models import VisualContext

class IFrameExtractor(ABC):
    @abstractmethod
    def extract_clip_samples(self, video_path: Path, start: float, end: float, fps: int) -> List[Any]:
        """Returns a list of PIL Images representing the clip."""
        pass

class IVisionModel(ABC):
    @abstractmethod
    def analyze_segment(self, images: List[Any], query: str, start: float, end: float) -> VisualContext:
        """Analyzes a sequence of images as a single event."""
        pass