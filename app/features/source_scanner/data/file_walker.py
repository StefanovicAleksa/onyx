import os
from pathlib import Path
from typing import Iterator
from ..domain.interfaces import IFileWalker
from .ignore_rules import IgnoreRules

class LocalFileWalker(IFileWalker):
    """
    Concrete implementation using standard os.walk for efficiency.
    """
    
    def walk(self, root: Path, recursive: bool) -> Iterator[Path]:
        if recursive:
            for dirpath, dirnames, filenames in os.walk(root):
                # 1. Filter directories in-place to prevent traversing ignored folders
                # Modifying 'dirnames' tells os.walk to skip them
                dirnames[:] = [
                    d for d in dirnames 
                    if not IgnoreRules.should_ignore(Path(d))
                ]
                
                # 2. Process files
                for filename in filenames:
                    file_path = Path(dirpath) / filename
                    
                    if not IgnoreRules.should_ignore(file_path):
                        yield file_path
        else:
            # Non-recursive: just iterate the immediate directory
            for item in root.iterdir():
                if item.is_file() and not IgnoreRules.should_ignore(item):
                    yield item