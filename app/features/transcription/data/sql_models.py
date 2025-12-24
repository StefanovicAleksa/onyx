import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Float, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.core.database.base import Base


def utc_now():
    return datetime.now(timezone.utc)


class TranscriptionModel(Base):
    """
    The Header record for a transcription.
    """
    __tablename__ = "transcriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False)

    language = Column(String, default="en")
    model_used = Column(String, nullable=False)

    # The Full Text Blob (Useful for basic "CTRL+F" search)
    full_text = Column(Text, nullable=False)

    # Processing stats (e.g. {"duration": 120.5, "device": "cuda"})
    processing_meta = Column(JSON, default=dict)

    created_at = Column(DateTime(timezone=True), default=utc_now)

    source = relationship("SourceModel", back_populates="transcriptions")
    job = relationship("JobModel")
    segments = relationship("TranscriptionSegmentModel", back_populates="transcription", cascade="all, delete-orphan")


class TranscriptionSegmentModel(Base):
    """
    The Atomic Unit.
    Includes rich metadata (confidence, timestamps) in JSONB.
    """
    __tablename__ = "transcription_segments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transcription_id = Column(UUID(as_uuid=True), ForeignKey("transcriptions.id"), nullable=False)

    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    text = Column(Text, nullable=False)

    # Link to Diarization Feature
    speaker_id = Column(UUID(as_uuid=True), ForeignKey("source_speakers.id"), nullable=True)

    # Rich Metadata Container
    meta_data = Column(JSON, default=dict)

    transcription = relationship("TranscriptionModel", back_populates="segments")

    # --- ADDED THIS RELATIONSHIP ---
    # We use a string reference "SourceSpeakerModel" to avoid circular imports.
    # This works as long as SourceSpeakerModel shares the same Base.
    speaker = relationship("SourceSpeakerModel", foreign_keys=[speaker_id])