import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.core.database.base import Base

def utc_now():
    return datetime.now(timezone.utc)

class VideoAudioModel(Base):
    """
    Links a Video Source to its extracted Audio Source.
    This allows us to skip extraction if we've already done it.
    
    Structure: [Video Source ID] --> [Audio Source ID]
    """
    __tablename__ = "video_audio_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # The parent video
    video_source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False)
    
    # The extracted audio (which is also a Source in the system)
    audio_source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=utc_now)