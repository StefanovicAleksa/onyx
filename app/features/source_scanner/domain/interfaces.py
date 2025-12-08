from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterator

class IFileWalker(ABC):
    """
    Contract for traversing a directory structure.
    Abstracts os.walk logic.
    """
    @abstractmethod
    def walk(self, root: Path, recursive: bool) -> Iterator[Path]:
        """
        Yields valid files one by one, filtering out system junk.
        """
        pass