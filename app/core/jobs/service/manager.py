import logging
from uuid import UUID
from ..domain.models import JobSubmission
from ..data.repository import PostgresJobRepo

logger = logging.getLogger(__name__)

class JobManager:
    """
    Public API for the Jobs Core Module.
    Handles 'Smart Deduplication' of compute tasks.
    """
    
    def __init__(self):
        # In a full DI framework, this would be injected.
        self.repo = PostgresJobRepo()

    def submit_job(self, submission: JobSubmission) -> UUID:
        """
        Submits a job for processing.
        Checks if the work has already been done for this physical file.
        
        Returns:
            UUID of the job (either new pending, or new completed-cached).
        """
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
