import shutil
import mimetypes
from pathlib import Path
from typing import Tuple
from app.core.config.settings import settings
from app.core.common.enums import FileType
from ..domain.interfaces import IFileSystem

class LocalFileSystem(IFileSystem):
    def move_to_artifacts(self, source: Path, file_hash: str) -> Tuple[Path, int]:
        """
        Moves input file to: data/artifacts/{first_2_chars_of_hash}/{full_hash}.ext
        This folder sharding prevents performance issues with thousands of files in one dir.
        """
        # 1. Get file size before moving
        file_size = source.stat().st_size
        
        # 2. Construct destination path
        extension = source.suffix.lower()
        sub_dir = settings.ARTIFACTS_DIR / file_hash[:2]
        sub_dir.mkdir(parents=True, exist_ok=True)
        
        destination = sub_dir / f"{file_hash}{extension}"
        
        # 3. Move file (Copy + Unlink is safer across different partitions/drives)
        if destination.exists():
            # If the physical file already exists (hash collision or re-upload), 
            # we don't need to overwrite it, just return it.
            return destination, destination.stat().st_size
            
        shutil.copy2(str(source), str(destination))
        source.unlink() # Remove the temp file
        
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