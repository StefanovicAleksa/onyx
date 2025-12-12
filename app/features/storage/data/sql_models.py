import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.core.database.base import Base
from app.core.common.enums import FileType, SourceType

def utc_now():
    return datetime.now(timezone.utc)

class FileModel(Base):
    __tablename__ = "files"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_path = Column(String, nullable=False, unique=True)
    file_size_bytes = Column(Integer, nullable=False)
    file_hash = Column(String, nullable=False, unique=True, index=True)
    file_type = Column(SQLEnum(FileType), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    
    # One physical file can be used by multiple logical sources (Deduplication)
    sources = relationship("SourceModel", back_populates="original_file")

class SourceModel(Base):
    __tablename__ = "sources"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    source_type = Column(SQLEnum(SourceType), nullable=False)
    file_id = Column(UUID(as_uuid=True), ForeignKey("files.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    # 1. Link to Parent File
    original_file = relationship("FileModel", back_populates="sources")

    # 2. Reverse Links (THE MISSING PIECE)
    # These allow other features to link back to Source without circular imports.
    
    # Linked to app/core/jobs/models.py
    jobs = relationship(
        "JobModel", 
        back_populates="source", 
        cascade="all, delete-orphan"
    )
    
    # Linked to app/features/transcription/data/sql_models.py
    transcriptions = relationship(
        "TranscriptionModel", 
        back_populates="source", 
        cascade="all, delete-orphan"
    )
    
    # Linked to app/features/diarization/data/sql_models.py
    identified_speakers = relationship(
        "SourceSpeakerModel", 
        back_populates="source", 
        cascade="all, delete-orphan"
    )