import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, JSON, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database.base import Base

def utc_now():
    return datetime.now(timezone.utc)

class SourceSpeakerModel(Base):
    """
    Represents a unique voice entity discovered in a Source.
    Owned by the Diarization Feature.
    """
    __tablename__ = "source_speakers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Link to the Source (File) this speaker appears in
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False)
    
    # The label assigned by the AI (e.g., "speaker_0")
    detected_label = Column(String, nullable=False) 
    
    # The human-readable name (starts same as detected, editable by user)
    # e.g., "Judge Judy"
    user_label = Column(String, nullable=False)
    
    # "The Intelligence Bucket" - Stores inferred attributes
    # e.g. { "role": "Defense Attorney", "gender": "Female", "tone": "Aggressive" }
    profile_meta = Column(JSON, default=dict)
    
    created_at = Column(DateTime(timezone=True), default=utc_now)
    
    # Relationship back to Source (optional for navigation)
    source = relationship("SourceModel", back_populates="identified_speakers")