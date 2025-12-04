from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class TimeRange:
    """
    Value Object representing a valid span of time.
    Enforces that start_time is strictly before end_time.
    """
    start_seconds: float
    end_seconds: float

    def __post_init__(self):
        if self.start_seconds < 0 or self.end_seconds < 0:
            raise ValueError("Timestamps cannot be negative.")
        if self.start_seconds >= self.end_seconds:
            raise ValueError(f"Start time ({self.start_seconds}) must be before end time ({self.end_seconds}).")

    @property
    def duration(self) -> float:
        return self.end_seconds - self.start_seconds

@dataclass(frozen=True)
class MediaFile:
    """
    Entity representing a media file on the filesystem.
    Encapsulates path validation and directory creation.
    """
    path: Path

    def __post_init__(self):
        if str(self.path).strip() == "." or str(self.path).strip() == "":
             raise ValueError("File path cannot be empty.")

    def exists(self) -> bool:
        return self.path.exists()

    def ensure_parent_dir(self) -> None:
        """Creates the directory structure for this file if it doesn't exist."""
        self.path.parent.mkdir(parents=True, exist_ok=True)