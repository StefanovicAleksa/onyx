from dataclasses import dataclass
from typing import List

@dataclass(frozen=True)
class VisualContext:
    """
    The AI's understanding of a specific video segment.
    """
    timestamp_start: float
    timestamp_end: float
    description: str      # "The user is circling a spike in the Q3 revenue chart."
    ocr_text: str         # "Revenue +15%" (Text extracted from the frames)
    confidence: float