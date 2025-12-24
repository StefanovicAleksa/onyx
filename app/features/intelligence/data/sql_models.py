import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Float, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.core.database.base import Base


def utc_now():
    return datetime.now(timezone.utc)


class IntelligenceSegmentModel(Base):
    __tablename__ = "intelligence_segments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False, index=True)
    context_window_id = Column(UUID(as_uuid=True), ForeignKey("context_windows.id"), nullable=True)

    title = Column(String, nullable=False)
    summary = Column(Text, nullable=False)
    keywords = Column(JSON, default=list)

    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)

    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    source = relationship("SourceModel")
    context_window = relationship("ContextWindowModel")