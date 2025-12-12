# File: app/core/jobs/manager.py

import logging
from uuid import UUID
from datetime import datetime, timezone
from app.core.database.connection import SessionLocal
from .models import JobModel
from .types import JobType, JobStatus

logger = logging.getLogger(__name__)

class JobManager:
    """
    The Central Dispatcher. 
    It doesn't know *how* to do the job, but it knows *who* can.
    """

    def submit_job(self, source_id: UUID, job_type: JobType, params: dict = {}) -> UUID:
        """Create a Job Record in PENDING state."""
        with SessionLocal() as db:
            job = JobModel(source_id=source_id, job_type=job_type, payload=params)
            db.add(job)
            db.commit()
            db.refresh(job)
            logger.info(f"Job Submitted: {job.id} [{job_type}]")
            return job.id

    def run_job(self, job_id: UUID):
        """
        Executes a specific job by routing it to the appropriate feature handler.
        """
        with SessionLocal() as db:
            job = db.get(JobModel, job_id)
            if not job:
                logger.error(f"Job {job_id} not found.")
                return
            
            # Update Status -> PROCESSING
            job.status = JobStatus.PROCESSING
            job.started_at = datetime.now(timezone.utc)
            db.commit()

            try:
                logger.info(f"Starting Job {job_id} ({job.job_type})...")
                
                # Dynamic Routing to Feature Handlers
                result = self._route_to_feature(job)

                # Update Status -> COMPLETED
                job.result_meta = result
                job.status = JobStatus.COMPLETED
                job.finished_at = datetime.now(timezone.utc)
                logger.info(f"Job {job_id} Completed successfully.")

            except NotImplementedError as e:
                # Configuration error
                job.status = JobStatus.FAILED
                job.error_message = f"Configuration Error: {str(e)}"
                logger.error(f"Job {job_id} Failed: {e}")

            except Exception as e:
                # Execution error
                job.status = JobStatus.FAILED
                job.error_message = str(e)
                logger.exception(f"Job {job_id} Failed: {e}")
            
            finally:
                db.commit()

    def _route_to_feature(self, job: JobModel) -> dict:
        """
        Routes the job to the correct Feature Handler.
        Uses lazy imports to prevent circular dependencies.
        """
        if job.job_type == JobType.TRANSCRIPTION:
            from app.features.transcription.service.job_handler import TranscriptionHandler
            return TranscriptionHandler().handle(job.source_id, job.payload)
            
        elif job.job_type == JobType.DIARIZATION:
            from app.features.diarization.service.job_handler import DiarizationHandler
            return DiarizationHandler().handle(job.source_id, job.payload)
            
        elif job.job_type == JobType.VAD_ANALYSIS:
            from app.features.vad.job_handler import VadHandler
            return VadHandler().handle(job.source_id, job.payload)

        # Future features...
        # elif job.job_type == JobType.AUDIO_EXTRACTION: ...
        
        raise NotImplementedError(f"No handler registered for JobType: {job.job_type}")