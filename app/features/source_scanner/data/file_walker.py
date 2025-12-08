import os
from pathlib import Path
from typing import Iterator

from ..domain.interfaces import IFileWalker
from .ignore_rules import IgnoreRules

class LocalFileWalker(IFileWalker):
    """
    Concrete implementation using os.walk.
    """
    
    def walk(self, root: Path, recursive: bool) -> Iterator[Path]:
        # If recursive, use os.walk
        if recursive:
            for dirpath, dirnames, filenames in os.walk(root):
                # 1. Filter directories in-place to prevent traversing them
                # (Modifying 'dirnames' list tells os.walk to skip them)
                dirnames[:] = [
                    d for d in dirnames 
                    if not IgnoreRules.should_ignore(Path(d))
                ]
                
                for filename in filenames:
                    file_path = Path(dirpath) / filename
                    
                    if not IgnoreRules.should_ignore(file_path):
                        yield file_path
        else:
            # Non-recursive: just list directory
            for item in root.iterdir():
                if item.is_file() and not IgnoreRules.should_ignore(item):
                    yield item