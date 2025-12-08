import shutil
import mimetypes
from pathlib import Path
from typing import Tuple

from app.core.config import settings
from app.core.enums import FileType
from ..domain.interfaces import IFileSystem

class LocalFileSystem(IFileSystem):
    def move_to_artifacts(self, source: Path, file_hash: str) -> Tuple[Path, int]:
        """
        Moves input file to data/artifacts/{hash_first_2_chars}/{hash}.ext
        This prevents having 10,000 files in a single directory.
        """
        # 1. Get file size
        file_size = source.stat().st_size
        
        # 2. Construct destination path
        # Structure: /data/artifacts/a1/a1b2c3d4...
        extension = source.suffix.lower()
        sub_dir = settings.ARTIFACTS_DIR / file_hash[:2]
        sub_dir.mkdir(parents=True, exist_ok=True)
        
        destination = sub_dir / f"{file_hash}{extension}"
        
        # 3. Move file (Copy then unlink is safer across partitions)
        shutil.move(str(source), str(destination))
        
        return destination, file_size

    def determine_file_type(self, path: Path) -> FileType:
        mime, _ = mimetypes.guess_type(path)
        if not mime:
            return FileType.UNKNOWN
            
        if mime.startswith("video"):
            return FileType.VIDEO
        if mime.startswith("audio"):
            return FileType.AUDIO
        if mime.startswith("image"):
            return FileType.IMAGE
        if mime.startswith("text"):
            return FileType.TEXT
            
        return FileType.UNKNOWN