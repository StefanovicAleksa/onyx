from dataclasses import dataclass, field
from pathlib import Path
from typing import List

@dataclass(frozen=True)
class ScanRequest:
    """
    User intent to scan a specific directory.
    """
    root_path: Path
    source_name_prefix: str = "" # Optional prefix for source names (e.g. "Case 409 - ")
    recursive: bool = True
    
    def __post_init__(self):
        if not self.root_path.exists():
            raise FileNotFoundError(f"Scan root not found: {self.root_path}")
        if not self.root_path.is_dir():
            raise NotADirectoryError(f"Scan root is not a directory: {self.root_path}")

@dataclass
class ScanSummary:
    """
    Report returned after scanning completes.
    """
    files_found: int = 0
    files_ingested: int = 0
    files_ignored: int = 0
    errors: List[str] = field(default_factory=list)