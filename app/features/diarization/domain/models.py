from dataclasses import dataclass

@dataclass
class DiarizationSegment:
    """
    A mapping of a time range to a Speaker Label.
    """
    start: float
    end: float
    speaker_label: str # "speaker_0", "speaker_1"

@dataclass
class DiarizationResult:
    source_id: str
    num_speakers: int
    segments: list[DiarizationSegment]