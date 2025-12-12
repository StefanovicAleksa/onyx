from abc import ABC, abstractmethod
from uuid import UUID
from typing import Optional, Tuple
from pathlib import Path
from app.core.common.enums import FileType

class IHasher(ABC):
    @abstractmethod
    def calculate_sha256(self, file_path: Path) -> str:
        """Calculates the SHA256 hash of a file."""
        pass

class IFileSystem(ABC):
    @abstractmethod
    def move_to_artifacts(self, source: Path, file_hash: str) -> Tuple[Path, int]:
        """
        Moves the file to the secure artifact storage.
        Returns: (new_absolute_path, file_size_bytes)
        """
        pass
    
    @abstractmethod
    def determine_file_type(self, path: Path) -> FileType:
        """Determines if file is VIDEO, AUDIO, etc."""
        pass

class IStorageRepository(ABC):
    @abstractmethod
    def get_file_by_hash(self, file_hash: str) -> Optional[dict]:
        """Checks if a file with this hash already exists."""
        pass

    @abstractmethod
    def create_source(self, file_data: dict, source_data: dict) -> UUID:
        """
        Creates a Source record and (optionally) a File record in one transaction.
        Returns the new Source ID.
        """
        pass