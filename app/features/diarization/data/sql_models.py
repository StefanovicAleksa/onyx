# File: app/features/diarization/data/sql_models.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, ForeignKey, DateTime, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.core.database.base import Base

def utc_now():
    return datetime.now(timezone.utc)

class SourceSpeakerModel(Base):
    """
    Identity Entity.
    Maps a raw 'speaker_0' label to a persistent identity for a Source.
    Allows the user to rename 'speaker_0' -> 'Dr. Smith' without breaking data.
    """
    __tablename__ = "source_speakers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False)
    
    # The label NeMo outputs (Machine ID)
    detected_label = Column(String, nullable=False) # e.g., "speaker_0"
    
    # The label the User sees (Human ID)
    user_label = Column(String, nullable=False)     # Defaults to "Unknown speaker_0"
    
    # Metadata for UI (e.g., "Voice profile color", "Avg Pitch")
    profile_meta = Column(JSON, default=dict)
    
    created_at = Column(DateTime(timezone=True), default=utc_now)

    source = relationship("SourceModel")
    
    # Ensure speaker_0 only exists once per source
    __table_args__ = (
        UniqueConstraint('source_id', 'detected_label', name='uix_source_speaker_label'),
    )