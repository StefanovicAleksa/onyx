from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class MediaFile:
    """
    Value Object representing a media file path.
    """
    path: Path
    validate_exists: bool = True
    
    def __post_init__(self):
        if self.validate_exists:
            if not self.path.exists():
                raise FileNotFoundError(f"Media file not found: {self.path}")
            if not self.path.is_file():
                raise ValueError(f"Path is not a file: {self.path}")

    def ensure_parent_dir(self):
        """Ensures the directory for this file exists."""
        self.path.parent.mkdir(parents=True, exist_ok=True)

@dataclass(frozen=True)
class TimeRange:
    start_seconds: float
    end_seconds: float
    
    def __post_init__(self):
        if self.start_seconds < 0:
            raise ValueError(f"Start time cannot be negative: {self.start_seconds}")
        if self.end_seconds <= self.start_seconds:
            raise ValueError(f"End time ({self.end_seconds}) must be greater than start time ({self.start_seconds})")
    
    @property
    def duration(self) -> float:
        return self.end_seconds - self.start_seconds

@dataclass(frozen=True)
class ClipRequest:
    source_video: MediaFile
    output_video: MediaFile
    time_range: TimeRange