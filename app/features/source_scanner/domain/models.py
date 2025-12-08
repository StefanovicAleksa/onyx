from dataclasses import dataclass, field
from pathlib import Path
from typing import List

@dataclass(frozen=True)
class ScanRequest:
    """
    DTO defining a bulk ingestion task.
    """
    root_path: Path
    source_name_prefix: str  # e.g. "Case File 101" -> "Case File 101 - document.pdf"
    recursive: bool = True

    def __post_init__(self):
        if not self.root_path.exists():
            raise FileNotFoundError(f"Scan root not found: {self.root_path}")
        if not self.root_path.is_dir():
            raise NotADirectoryError(f"Scan root must be a directory: {self.root_path}")

@dataclass
class ScanSummary:
    """
    Result report for a scan operation.
    """
    files_found: int = 0
    files_ingested: int = 0
    errors: List[str] = field(default_factory=list)