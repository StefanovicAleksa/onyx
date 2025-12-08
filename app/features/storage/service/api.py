from uuid import UUID
from app.core.enums import SourceType
from ..domain.models import IngestRequest
from ..data.hasher import SHA256Hasher
from ..data.local_fs import LocalFileSystem
from ..data.repository import PostgresStorageRepo

def ingest_file(request: IngestRequest) -> UUID:
    """
    Orchestrates the ingestion process:
    1. Calculate Hash
    2. Check DB for duplicates
    3. Move file to Artifacts (if new) OR Link to existing
    4. Save to DB
    """
    # 1. Instantiate dependencies
    hasher = SHA256Hasher()
    fs = LocalFileSystem()
    repo = PostgresStorageRepo()
    
    # 2. Calculate Hash
    file_hash = hasher.calculate_sha256(request.file_path)
    
    # 3. Check Deduplication
    existing_file = repo.get_file_by_hash(file_hash)
    
    if existing_file:
        # Optimization: File exists on disk.
        # We DO NOT move the new file. We just delete the temp upload.
        request.file_path.unlink()
        
        final_path = existing_file.file_path
        file_size = existing_file.file_size_bytes
        file_type = existing_file.file_type
    else:
        # New File: Move it physically to artifacts
        path_obj, file_size = fs.move_to_artifacts(request.file_path, file_hash)
        final_path = str(path_obj)
        file_type = fs.determine_file_type(path_obj)

    # 4. Prepare DB Data
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
    
    # 5. Commit to DB
    # The repo handles the logic of reusing the File ID if it exists
    source_id = repo.create_entry(file_data, source_data)
    
    return source_id