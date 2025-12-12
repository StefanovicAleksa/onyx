import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.core.database.base import Base

def utc_now():
    return datetime.now(timezone.utc)

class TranscriptionModel(Base):
    """
    The Header record for a transcription.
    Links a Source to its text representation.
    """
    __tablename__ = "transcriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relationships
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False)
    
    # Metadata
    language = Column(String, default="en")
    model_used = Column(String, nullable=False)
    
    # The Full Text Blob (Useful for basic "CTRL+F" search)
    full_text = Column(Text, nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=utc_now)

    # Navigation Properties
    source = relationship("SourceModel", back_populates="transcriptions")
    job = relationship("JobModel")
    segments = relationship("TranscriptionSegmentModel", back_populates="transcription", cascade="all, delete-orphan")

class TranscriptionSegmentModel(Base):
    """
    The Atomic Unit.
    These rows will be the primary targets for Vector Search (RAG) later.
    """
    __tablename__ = "transcription_segments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transcription_id = Column(UUID(as_uuid=True), ForeignKey("transcriptions.id"), nullable=False)
    
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    text = Column(Text, nullable=False)
    
    # Link to Diarization Feature
    # We references the table name "source_speakers" directly to avoid 
    # circular Python imports between Feature modules.
    speaker_id = Column(UUID(as_uuid=True), ForeignKey("source_speakers.id"), nullable=True)

    transcription = relationship("TranscriptionModel", back_populates="segments")