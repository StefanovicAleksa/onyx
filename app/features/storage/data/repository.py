from uuid import UUID
from typing import Optional
from sqlalchemy.orm import Session
from app.core.database.connection import SessionLocal
from .sql_models import FileModel, SourceModel
from ..domain.interfaces import IStorageRepository

class PostgresStorageRepo(IStorageRepository):
    def get_file_by_hash(self, file_hash: str) -> Optional[FileModel]:
        with SessionLocal() as db:
            return db.query(FileModel).filter(FileModel.file_hash == file_hash).first()

    def create_source(self, file_data: dict, source_data: dict) -> UUID:
        """
        Transactional logic:
        1. Check if File exists (Deduplication).
        2. If not, insert File.
        3. Insert Source linked to File.
        """
        with SessionLocal() as db:
            try:
                # 1. Deduplication Check
                existing_file = db.query(FileModel).filter(
                    FileModel.file_hash == file_data["file_hash"]
                ).first()
                
                if existing_file:
                    file_id = existing_file.id
                else:
                    # 2. Create New File Record
                    new_file = FileModel(**file_data)
                    db.add(new_file)
                    db.flush() # Flush to generate ID
                    file_id = new_file.id
                
                # 3. Create Source Record
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