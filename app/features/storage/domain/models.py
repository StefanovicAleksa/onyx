from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
from app.core.common.enums import SourceType, FileType

@dataclass(frozen=True)
class IngestRequest:
    """
    Request object for ingesting a new file.
    """
    file_path: Path
    source_name: str
    source_type: SourceType

    def __post_init__(self):
        # Validate existence immediately upon creation
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {self.file_path}")

@dataclass
class StoredFile:
    """
    Represents a physical file stored in the artifact repository.
    """
    id: str
    path: str
    hash: str
    size_bytes: int
    file_type: FileType
    created_at: datetime