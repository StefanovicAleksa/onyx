from dataclasses import dataclass

@dataclass(frozen=True)
class SpeechSegment:
    """
    Represents a time range containing active speech.
    """
    start: float
    end: float
    confidence: float = 1.0

    @property
    def duration(self) -> float:
        return self.end - self.start