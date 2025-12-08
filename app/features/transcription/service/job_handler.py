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
    def __init__(self): self.adapter = None 

    def _get_adapter(self, model_size: str):
        if not self.adapter or self.adapter.model_size != model_size:
            self.adapter = WhisperAdapter(model_size=model_size)
        return self.adapter

    def handle(self, job_id: UUID):
        logger.info(f"📝 Starting Transcription Job: {job_id}")
        with SessionLocal() as db:
            job = db.get(JobModel, job_id)
            try:
                # BUGFIX: Wrapping path in Path() object
                audio_path = Path(job.source.original_file.file_path)
                job.status = JobStatus.PROCESSING
                db.commit()

                adapter = self._get_adapter(job.payload.get("model_size", "large-v3"))
                result = adapter.transcribe(MediaFile(audio_path))
                
                job.status = JobStatus.COMPLETED
                job.meta = dataclasses.asdict(result)
                if "source_audio" in job.meta: job.meta["source_audio"] = str(result.source_audio.path)
                logger.info(f"✅ Transcription Success.")
            except Exception as e:
                logger.error(f"❌ Transcription Failed: {e}")
                job.status = JobStatus.FAILED
                job.error_message = str(e)
            finally: db.commit()
