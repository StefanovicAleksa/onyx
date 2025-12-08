import logging
import dataclasses
from pathlib import Path
from uuid import UUID

from app.core.database import SessionLocal
from app.core.db_models import JobModel, JobStatus
from app.core.shared_types import MediaFile

from ..data.whisper_adapter import WhisperAdapter

logger = logging.getLogger(__name__)

class TranscriptionHandler:
    """
    Worker logic that executes a TRANSCRIPTION job.
    """
    
    def __init__(self):
        # In a real worker, we might keep this warm or load it on demand
        self.adapter = None 

    def _get_adapter(self, model_size: str):
        if not self.adapter or self.adapter.model_size != model_size:
            self.adapter = WhisperAdapter(model_size=model_size)
        return self.adapter

    def handle(self, job_id: UUID):
        """
        Orchestrates the transcription process:
        1. Fetch Job & Source File
        2. Run Whisper
        3. Save Transcript to Job Meta
        """
        logger.info(f"📝 Starting Transcription Job: {job_id}")
        
        with SessionLocal() as db:
            job = db.get(JobModel, job_id)
            if not job:
                raise ValueError(f"Job {job_id} not found")
            
            try:
                # 1. Prepare
                audio_path = Path(job.source.original_file.file_path)
                model_size = job.payload.get("model_size", "large-v3")
                
                # 2. Update Status
                job.started_at = job.created_at
                job.status = JobStatus.PROCESSING
                db.commit()

                # 3. Transcribe
                adapter = self._get_adapter(model_size)
                result = adapter.transcribe(MediaFile(audio_path))
                
                # 4. Save Result
                # We serialize the Domain Entity (TranscriptionResult) to a dict
                # so it can be stored in the JSONB 'meta' column.
                job.status = JobStatus.COMPLETED
                job.meta = dataclasses.asdict(result)
                # Remove the path object from meta as it's not JSON serializable by default
                if "source_audio" in job.meta:
                    job.meta["source_audio"] = str(result.source_audio.path)

                logger.info(f"✅ Transcription Success. Length: {len(result.full_text)} chars")
                
            except Exception as e:
                logger.error(f"❌ Transcription Failed: {e}")
                job.status = JobStatus.FAILED
                job.error_message = str(e)
            finally:
                db.commit()
