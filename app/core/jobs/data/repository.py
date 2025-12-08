from typing import Optional, Dict, Any
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

    def find_completed_sibling(self, file_id: UUID, job_type: JobType, payload: Dict[str, Any]) -> Optional[JobModel]:
        with SessionLocal() as db:
            query = (db.query(JobModel)
                .join(SourceModel, JobModel.source_id == SourceModel.id)
                .filter(SourceModel.file_id == file_id, JobModel.job_type == job_type, JobModel.status == JobStatus.COMPLETED))
            candidates = query.all()
            for job in candidates:
                if job.payload == payload: return job
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
            if is_cached: new_job.finished_at = new_job.created_at
            db.add(new_job)
            db.commit()
            db.refresh(new_job)
            return new_job.id
