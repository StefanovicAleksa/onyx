from abc import ABC, abstractmethod
from uuid import UUID
from pathlib import Path
from typing import Tuple, Optional

from app.core.db_models import FileModel
from app.core.enums import FileType

class IHasher(ABC):
    """Contract for calculating file checksums."""
    @abstractmethod
    def calculate_sha256(self, file_path: Path) -> str:
        pass

class IFileSystem(ABC):
    """Contract for physical file operations."""
    @abstractmethod
    def move_to_artifacts(self, source: Path, file_hash: str) -> Tuple[Path, int]:
        """
        Moves file to secure storage.
        Returns (new_absolute_path, file_size_bytes).
        """
        pass
    
    @abstractmethod
    def determine_file_type(self, path: Path) -> FileType:
        """Detects if file is VIDEO, AUDIO, etc."""
        pass

class IStorageRepository(ABC):
    """Contract for Database interactions."""
    @abstractmethod
    def get_file_by_hash(self, file_hash: str) -> Optional[FileModel]:
        """Checks if we already have this file."""
        pass

    @abstractmethod
    def create_entry(self, 
                     file_data: dict, 
                     source_data: dict) -> UUID:
        """
        Transactional insert. 
        Returns the new Source ID.
        """
        pass