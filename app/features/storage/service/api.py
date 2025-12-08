from uuid import UUID
from app.core.enums import SourceType
from ..domain.models import IngestRequest
from ..data.hasher import SHA256Hasher
from ..data.local_fs import LocalFileSystem
from ..data.repository import PostgresStorageRepo

def ingest_file(request: IngestRequest) -> UUID:
    hasher = SHA256Hasher()
    fs = LocalFileSystem()
    repo = PostgresStorageRepo()
    
    file_hash = hasher.calculate_sha256(request.file_path)
    existing_file = repo.get_file_by_hash(file_hash)
    
    if existing_file:
        request.file_path.unlink()
        final_path = existing_file.file_path
        file_size = existing_file.file_size_bytes
        file_type = existing_file.file_type
    else:
        path_obj, file_size = fs.move_to_artifacts(request.file_path, file_hash)
        final_path = str(path_obj)
        file_type = fs.determine_file_type(path_obj)

    return repo.create_entry({
        "file_path": final_path, "file_size_bytes": file_size,
        "file_hash": file_hash, "file_type": file_type
    }, { "name": request.source_name, "source_type": request.source_type })
