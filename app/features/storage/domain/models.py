from dataclasses import dataclass
from pathlib import Path
from app.core.enums import SourceType

@dataclass(frozen=True)
class IngestRequest:
    file_path: Path
    source_name: str
    source_type: SourceType
    def __post_init__(self):
        if not self.file_path.exists(): raise FileNotFoundError(f"File not found: {self.file_path}")
