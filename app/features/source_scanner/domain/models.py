from dataclasses import dataclass, field
from pathlib import Path
from typing import List

@dataclass(frozen=True)
class ScanRequest:
    root_path: Path
    source_name_prefix: str
    recursive: bool = True

@dataclass
class ScanSummary:
    files_found: int = 0
    files_ingested: int = 0
    errors: List[str] = field(default_factory=list)
