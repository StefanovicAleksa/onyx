import os
from pathlib import Path

# Base paths
BASE_DIR = Path("app/core/jobs")
DOMAIN_DIR = BASE_DIR / "domain"
DATA_DIR = BASE_DIR / "data"
SERVICE_DIR = BASE_DIR / "service"

# Ensure directories exist
for d in [DOMAIN_DIR, DATA_DIR, SERVICE_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Create __init__.py files
for d in [BASE_DIR, DOMAIN_DIR, DATA_DIR, SERVICE_DIR]:
    (d / "__init__.py").touch()

# --- FILE CONTENTS ---

# 1. Domain Models
models_code = """from dataclasses import dataclass, field
from typing import Dict, Any
from uuid import UUID
from app.core.enums import JobType

@dataclass(frozen=True)
class JobSubmission:
    \"\"\"
    DTO for requesting a new job.
    \"\"\"
    source_id: UUID
    job_type: JobType
    payload: Dict[str, Any] = field(default_factory=dict)
"""

# 2. Domain Interfaces
interfaces_code = """from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from uuid import UUID

from app.core.db_models import JobModel
from app.core.enums import JobType
from .models import JobSubmission

class IJobRepository(ABC):
    \"\"\"
    Contract for Job persistence.
    Abstracts the logic of finding 'Sibling Jobs' (Compute Deduplication).
    \"\"\"
    
    @abstractmethod
    def find_completed_sibling(self, 
                               file_id: UUID, 
                               job_type: JobType, 
                               payload: Dict[str, Any]) -> Optional[JobModel]:
        \"\"\"
        Finds a COMPLETED job that ran on the SAME physical file (file_id)
        with the EXACT same parameters (payload).
        \"\"\"
        pass

    @abstractmethod
    def create_job(self, submission: JobSubmission, is_cached: bool = False, cached_meta: dict = None) -> UUID:
        \"\"\"
        Creates a new Job record.
        If is_cached is True, creates it as COMPLETED with cached_meta.
        If is_cached is False, creates it as PENDING.
        \"\"\"
        pass
    
    @abstractmethod
    def get_file_id_for_source(self, source_id: UUID) -> Optional[UUID]:
        \"\"\"
        Helper to resolve a Source ID to its physical File ID.
        \"\"\"
        pass
"""

# 3. Data Repository
repo_code = """from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.db_models import JobModel, SourceModel
from app.core.enums import JobStatus, JobType
from ..domain.interfaces import IJobRepository
from ..domain.models import JobSubmission

class PostgresJobRepo(IJobRepository):
    
    def get_file_id_for_source(self, source_id: UUID) -> Optional[UUID]:
        with SessionLocal() as db:
            source = db.query(SourceModel).filter(SourceModel.id == source_id).first()
            return source.file_id if source else None

    def find_completed_sibling(self, 
                               file_id: UUID, 
                               job_type: JobType, 
                               payload: Dict[str, Any]) -> Optional[JobModel]:
        \"\"\"
        Queries the DB for any job that:
        1. Is linked to a Source that points to THIS file_id.
        2. Has the same JobType.
        3. Is COMPLETED.
        4. Has the same configuration (payload).
        \"\"\"
        with SessionLocal() as db:
            # Join Job -> Source. Filter by Source.file_id
            query = (
                db.query(JobModel)
                .join(SourceModel, JobModel.source_id == SourceModel.id)
                .filter(
                    SourceModel.file_id == file_id,
                    JobModel.job_type == job_type,
                    JobModel.status == JobStatus.COMPLETED
                )
            )
            
            # Optimization: If payload is empty, just take the first match.
            # Otherwise, we need to ensure parameters match.
            candidates = query.all()
            
            for job in candidates:
                # Python-side comparison of dictionaries for exact match
                if job.payload == payload:
                    return job
                    
            return None

    def create_job(self, submission: JobSubmission, is_cached: bool = False, cached_meta: dict = None) -> UUID:
        with SessionLocal() as db:
            new_job = JobModel(
                source_id=submission.source_id,
                job_type=submission.job_type,
                payload=submission.payload,
                status=JobStatus.COMPLETED if is_cached else JobStatus.PENDING,
                meta=cached_meta if cached_meta else {}
            )
            
            if is_cached:
                new_job.finished_at = new_job.created_at # Instant finish
                
            db.add(new_job)
            db.commit()
            db.refresh(new_job)
            return new_job.id
"""

# 4. Service Manager
manager_code = """import logging
from uuid import UUID
from ..domain.models import JobSubmission
from ..data.repository import PostgresJobRepo

logger = logging.getLogger(__name__)

class JobManager:
    \"\"\"
    Public API for the Jobs Core Module.
    Handles 'Smart Deduplication' of compute tasks.
    \"\"\"
    
    def __init__(self):
        # In a full DI framework, this would be injected.
        self.repo = PostgresJobRepo()

    def submit_job(self, submission: JobSubmission) -> UUID:
        \"\"\"
        Submits a job for processing.
        Checks if the work has already been done for this physical file.
        
        Returns:
            UUID of the job (either new pending, or new completed-cached).
        \"\"\"
        # 1. Resolve Logical Source -> Physical File
        file_id = self.repo.get_file_id_for_source(submission.source_id)
        
        if not file_id:
            raise ValueError(f"Source {submission.source_id} does not exist or has no file linked.")

        # 2. Check for "Sibling Jobs" (Compute Cache)
        cached_job = self.repo.find_completed_sibling(
            file_id=file_id,
            job_type=submission.job_type,
            payload=submission.payload
        )

        if cached_job:
            logger.info(f"✨ CACHE HIT: Reusing result from Job {cached_job.id} for Source {submission.source_id}")
            # 3a. Create Instant Clone
            return self.repo.create_job(
                submission=submission,
                is_cached=True,
                cached_meta=cached_job.meta # Copy the results (e.g. transcript text)
            )
        else:
            logger.info(f"⚙️  CACHE MISS: Scheduling new compute for Source {submission.source_id}")
            # 3b. Create Pending Job (Worker will pick this up)
            return self.repo.create_job(
                submission=submission,
                is_cached=False
            )
"""

# Write files
files = {
    DOMAIN_DIR / "models.py": models_code,
    DOMAIN_DIR / "interfaces.py": interfaces_code,
    DATA_DIR / "repository.py": repo_code,
    SERVICE_DIR / "manager.py": manager_code,
}

for path, content in files.items():
    print(f"Generating {path}...")
    with open(path, "w") as f:
        f.write(content)

print("✅ Jobs Module created successfully.")