# File: app/features/context_pipeline/data/sql_models.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.core.database.base import Base

def utc_now():
    return datetime.now(timezone.utc)

class ContextWindowModel(Base):
    """
    Represents a specific 'Chunk' of text sent to the AI.
    """
    __tablename__ = "context_windows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False, index=True)
    
    window_index = Column(Integer, nullable=False) # 0, 1, 2...
    text_content = Column(Text, nullable=False)    # The actual blob sent to AI
    token_count = Column(Integer, nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=utc_now)

    # Relationships
    source = relationship("SourceModel")
    
    # The Provenance Link
    segment_links = relationship("WindowSegmentLink", back_populates="window", cascade="all, delete-orphan")

class WindowSegmentLink(Base):
    """
    The 'Rosetta Stone' Table.
    Maps a Window (AI View) back to specific Transcript Segments (User View).
    Allows queries like: "Show me the video clip for the 3rd sentence in this AI summary."
    """
    __tablename__ = "window_segment_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    window_id = Column(UUID(as_uuid=True), ForeignKey("context_windows.id"), nullable=False)
    # Maps to app/features/transcription/data/sql_models.py
    transcription_segment_id = Column(UUID(as_uuid=True), ForeignKey("transcription_segments.id"), nullable=False)
    
    # Optional: We could store the relative order in the window if segments get re-ordered
    sequence_order = Column(Integer, default=0)

    window = relationship("ContextWindowModel", back_populates="segment_links")
    segment = relationship("TranscriptionSegmentModel")