from dataclasses import dataclass, field
from typing import Dict, Any
from uuid import UUID
from app.core.enums import JobType

@dataclass(frozen=True)
class JobSubmission:
    """
    DTO for requesting a new job.
    """
    source_id: UUID
    job_type: JobType
    payload: Dict[str, Any] = field(default_factory=dict)
