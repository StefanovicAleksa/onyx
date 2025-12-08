import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base
from app.core.enums import FileType, SourceType, JobType, JobStatus

# Helper for timezone-aware UTC now
# This replaces the deprecated datetime.utcnow()
def utc_now():
    return datetime.now(timezone.utc)

class FileModel(Base):
    """
    Represents a physical file on the disk (Artifacts or Uploads).
    """
    __tablename__ = "files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_path = Column(String, nullable=False, unique=True) # Absolute path
    file_size_bytes = Column(Integer, nullable=False)
    file_hash = Column(String, nullable=True, index=True) # SHA256 for duplicate detection
    file_type = Column(SQLEnum(FileType), nullable=False)
    
    # Updated: Use timezone-aware datetime
    created_at = Column(DateTime(timezone=True), default=utc_now)
    
    # Relationships
    sources = relationship("SourceModel", back_populates="original_file")


class SourceModel(Base):
    """
    Represents a logical input provided by the user (e.g., 'Project Alpha Deposition').
    Links to the raw file.
    """
    __tablename__ = "sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False) # User-friendly name
    source_type = Column(SQLEnum(SourceType), nullable=False)
    
    # Foreign Key to the physical file
    file_id = Column(UUID(as_uuid=True), ForeignKey("files.id"), nullable=False)
    
    # Updated: Use timezone-aware datetime
    created_at = Column(DateTime(timezone=True), default=utc_now)

    # Relationships
    original_file = relationship("FileModel", back_populates="sources")
    jobs = relationship("JobModel", back_populates="source")


class JobModel(Base):
    """
    Represents a unit of work (Task).
    The core of the resumability system.
    """
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # What are we working on?
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False)
    
    # What are we doing?
    job_type = Column(SQLEnum(JobType), nullable=False)
    
    # State Tracking
    status = Column(SQLEnum(JobStatus), default=JobStatus.PENDING, nullable=False, index=True)
    error_message = Column(String, nullable=True)
    
    # Timing (Updated to timezone-aware)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    # Resumability & Context
    # 'payload': Arguments to start the job (e.g., model_size="large", time_range)
    payload = Column(JSON, default=dict) 
    
    # 'meta': Progress tracking (e.g., { "processed_chunks": 5, "last_timestamp": 120.5 })
    # If the system crashes, the worker reads this to know where to resume.
    meta = Column(JSON, default=dict)

    # Relationships
    source = relationship("SourceModel", back_populates="jobs")