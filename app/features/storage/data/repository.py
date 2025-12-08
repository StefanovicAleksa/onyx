from uuid import UUID
from typing import Optional
from app.core.database import SessionLocal
from app.core.db_models import FileModel, SourceModel
from ..domain.interfaces import IStorageRepository

class PostgresStorageRepo(IStorageRepository):
    """
    Concrete implementation using SQLAlchemy.
    """
    
    def get_file_by_hash(self, file_hash: str) -> Optional[FileModel]:
        with SessionLocal() as db:
            return db.query(FileModel).filter(FileModel.file_hash == file_hash).first()

    def create_entry(self, file_data: dict, source_data: dict) -> UUID:
        """
        Inserts FileModel (if needed) and SourceModel in a single transaction.
        """
        with SessionLocal() as db:
            try:
                # 1. Check for existing file (Double check inside txn for safety)
                # We use the file_hash from the incoming dictionary
                existing_file = db.query(FileModel).filter(
                    FileModel.file_hash == file_data["file_hash"]
                ).first()
                
                if existing_file:
                    file_id = existing_file.id
                else:
                    # Create new File record
                    new_file = FileModel(**file_data)
                    db.add(new_file)
                    db.flush() # Flush to get the ID
                    file_id = new_file.id
                
                # 2. Create Source record linked to file
                new_source = SourceModel(
                    **source_data,
                    file_id=file_id
                )
                db.add(new_source)
                
                db.commit()
                db.refresh(new_source)
                return new_source.id
                
            except Exception as e:
                db.rollback()
                raise e