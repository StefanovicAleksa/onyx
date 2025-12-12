import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.core.database.base import Base
from .types import JobType, JobStatus

def utc_now():
    return datetime.now(timezone.utc)

class JobModel(Base):
    __tablename__ = "jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # FIXED: Added ForeignKey("sources.id")
    # This tells the database that 'source_id' links to the 'sources' table.
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False, index=True) 
    
    job_type = Column(SQLEnum(JobType), nullable=False)
    status = Column(SQLEnum(JobStatus), default=JobStatus.PENDING)
    
    payload = Column(JSON, default=dict)     # Input parameters
    result_meta = Column(JSON, default=dict) # Output pointers (IDs, counts)
    
    created_at = Column(DateTime(timezone=True), default=utc_now)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    
    error_message = Column(String, nullable=True)

    # FIXED: Added the reverse relationship
    # This matches SourceModel.jobs (back_populates="source")
    source = relationship("SourceModel", back_populates="jobs")