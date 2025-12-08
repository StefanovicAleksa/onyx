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
    3. Move file to Artifacts
    4. Save to DB
    """
    # 1. Instantiate dependencies
    hasher = SHA256Hasher()
    fs = LocalFileSystem()
    repo = PostgresStorageRepo()
    
    # 2. Calculate Hash
    file_hash = hasher.calculate_sha256(request.file_path)
    
    # 3. Check Deduplication
    # (Optional optimization: if exists, skip move, just link source)
    existing_file = repo.get_file_by_hash(file_hash)
    
    if existing_file:
        # File exists on disk, we just create a new Source pointer
        final_path = existing_file.file_path
        file_size = existing_file.file_size_bytes
        file_type = existing_file.file_type
        # We can delete the uploaded temp file since we already have it
        request.file_path.unlink()
    else:
        # 4. Move to Storage
        path_obj, file_size = fs.move_to_artifacts(request.file_path, file_hash)
        final_path = str(path_obj)
        file_type = fs.determine_file_type(path_obj)

    # 5. Prepare DB Data
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
    
    # 6. Commit to DB
    source_id = repo.create_entry(file_data, source_data)
    
    return source_id