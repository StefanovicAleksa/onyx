import hashlib
from pathlib import Path
from ..domain.interfaces import IHasher

class SHA256Hasher(IHasher):
    def calculate_sha256(self, file_path: Path) -> str:
        """
        Streams the file in 64kb chunks to avoid loading large videos into RAM.
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            # Read in 64kb chunks
            for byte_block in iter(lambda: f.read(65536), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()