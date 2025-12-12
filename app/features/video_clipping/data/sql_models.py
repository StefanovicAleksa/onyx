import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.core.database.base import Base

def utc_now():
    return datetime.now(timezone.utc)

class VideoClipModel(Base):
    """
    Tracks the lineage of a clipped video.
    
    Relationships:
    - Parent Source (The original full-length video)
    - Clip Source (The newly created short video artifact)
    """
    __tablename__ = "video_clips"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # The source we cut FROM
    parent_source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False)
    
    # The source we created (The Clip)
    clip_source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False, unique=True)
    
    # Metadata for the cut
    start_time_seconds = Column(Float, nullable=False)
    end_time_seconds = Column(Float, nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=utc_now)