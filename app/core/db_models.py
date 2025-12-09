import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum as SQLEnum, JSON, Float, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base
from app.core.enums import FileType, SourceType, JobType, JobStatus

def utc_now():
    return datetime.now(timezone.utc)

# --- BASE MODELS ---
class FileModel(Base):
    __tablename__ = "files"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_path = Column(String, nullable=False, unique=True)
    file_size_bytes = Column(Integer, nullable=False, index=True) 
    file_hash = Column(String, nullable=False, unique=True, index=True)
    file_type = Column(SQLEnum(FileType), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    
    sources = relationship("SourceModel", back_populates="original_file")

class SourceModel(Base):
    __tablename__ = "sources"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    source_type = Column(SQLEnum(SourceType), nullable=False)
    file_id = Column(UUID(as_uuid=True), ForeignKey("files.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    original_file = relationship("FileModel", back_populates="sources")
    jobs = relationship("JobModel", back_populates="source")
    derived_audio_links = relationship("VideoAudioModel", back_populates="source")
    # New: Link to transcriptions
    transcriptions = relationship("TranscriptionModel", back_populates="source")

class JobModel(Base):
    __tablename__ = "jobs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False)
    job_type = Column(SQLEnum(JobType), nullable=False)
    status = Column(SQLEnum(JobStatus), default=JobStatus.PENDING, nullable=False, index=True)
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    payload = Column(JSON, default=dict) 
    meta = Column(JSON, default=dict)

    source = relationship("SourceModel", back_populates="jobs")

class VideoAudioModel(Base):
    __tablename__ = "video_audios"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False)
    audio_file_id = Column(UUID(as_uuid=True), ForeignKey("files.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    source = relationship("SourceModel", back_populates="derived_audio_links")
    audio_file = relationship("FileModel")

# --- NEW TRANSCRIPTION MODELS ---

class TranscriptionModel(Base):
    """
    The High-Level Result.
    """
    __tablename__ = "transcriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False)
    
    language = Column(String, default="en")
    model_used = Column(String, nullable=False)
    full_text = Column(Text, nullable=False) # Searchable text blob
    
    created_at = Column(DateTime(timezone=True), default=utc_now)

    source = relationship("SourceModel", back_populates="transcriptions")
    job = relationship("JobModel")
    segments = relationship("TranscriptionSegmentModel", back_populates="transcription", cascade="all, delete-orphan")

class TranscriptionSegmentModel(Base):
    """
    The Atomic Unit of Intelligence.
    We will eventually generate Vectors (Embeddings) for these rows.
    """
    __tablename__ = "transcription_segments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transcription_id = Column(UUID(as_uuid=True), ForeignKey("transcriptions.id"), nullable=False)
    
    start_time = Column(Float, nullable=False) # Key for Video Seeking
    end_time = Column(Float, nullable=False)
    text = Column(Text, nullable=False)

    transcription = relationship("TranscriptionModel", back_populates="segments")
