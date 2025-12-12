from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterator

class IFileWalker(ABC):
    """
    Contract for traversing a filesystem.
    Abstracts os.walk vs pathlib.
    """
    @abstractmethod
    def walk(self, root: Path, recursive: bool) -> Iterator[Path]:
        """
        Yields valid file paths one by one.
        Should handle filtering of system/hidden files internally.
        """
        pass