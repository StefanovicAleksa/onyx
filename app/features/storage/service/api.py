from uuid import UUID
from ..domain.models import IngestRequest
from ..data.hasher import SHA256Hasher
from ..data.local_fs import LocalFileSystem
from ..data.repository import PostgresStorageRepo

class StorageService:
    """
    Facade for the Storage Feature.
    Orchestrates Hashing, Filesystem operations, and Database persistence.
    """
    def __init__(self):
        self.hasher = SHA256Hasher()
        self.fs = LocalFileSystem()
        self.repo = PostgresStorageRepo()

    def ingest_file(self, request: IngestRequest) -> UUID:
        """
        Ingests a file into the system.
        - Calculates Hash.
        - Checks for duplicates (Smart Deduplication).
        - Moves file to secure artifacts folder.
        - Creates Database entries.
        
        Returns:
            UUID of the created Source.
        """
        # 1. Calculate Hash
        file_hash = self.hasher.calculate_sha256(request.file_path)
        
        # 2. Check Deduplication (Optimization: Check DB before moving file)
        # Note: In a distributed system, we might still move it to be safe,
        # but for local appliance, we can check DB first to save disk IO.
        existing_file = self.repo.get_file_by_hash(file_hash)
        
        if existing_file:
            # OPTIMIZATION: If file exists physically, we don't need to copy it again.
            # We just create a new Source pointing to the old File.
            # We delete the temp upload.
            request.file_path.unlink()
            
            final_path = existing_file.file_path
            file_size = existing_file.file_size_bytes
            file_type = existing_file.file_type
        else:
            # 3. Move to Artifacts
            path_obj, file_size = self.fs.move_to_artifacts(request.file_path, file_hash)
            final_path = str(path_obj)
            file_type = self.fs.determine_file_type(path_obj)

        # 4. Persist
        file_data = {
            "file_path": final_path,
            "file_size_bytes": file_size,
            "file_hash": file_hash,
            "file_type": file_type
        }
        
        source_data = {
            "name": request.source_name,
            "source_type": request.source_type
        }

        return self.repo.create_source(file_data, source_data)

# Singleton Instance for easy import
storage = StorageService()