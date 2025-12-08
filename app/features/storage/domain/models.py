from dataclasses import dataclass
from pathlib import Path
from app.core.enums import SourceType

@dataclass(frozen=True)
class IngestRequest:
    """
    DTO capturing the user's intent to ingest a file.
    """
    file_path: Path
    source_name: str
    source_type: SourceType

    def __post_init__(self):
        if not self.file_path.exists():
            raise FileNotFoundError(f"File to ingest not found: {self.file_path}")
        if not self.file_path.is_file():
            raise ValueError(f"Path is not a file: {self.file_path}")