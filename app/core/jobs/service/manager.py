import logging
from uuid import UUID
from ..domain.models import JobSubmission
from ..data.repository import PostgresJobRepo

logger = logging.getLogger(__name__)

class JobManager:
    def __init__(self):
        self.repo = PostgresJobRepo()

    def submit_job(self, submission: JobSubmission) -> UUID:
        file_id = self.repo.get_file_id_for_source(submission.source_id)
        if not file_id: raise ValueError(f"Source {submission.source_id} does not exist.")

        cached_job = self.repo.find_completed_sibling(file_id, submission.job_type, submission.payload)
        if cached_job:
            logger.info(f"✨ CACHE HIT: Reusing Job {cached_job.id}")
            return self.repo.create_job(submission, is_cached=True, cached_meta=cached_job.meta)
        else:
            logger.info("⚙️  CACHE MISS: Scheduling new job")
            return self.repo.create_job(submission, is_cached=False)
