import logging
import dataclasses
from pathlib import Path
from uuid import UUID

from app.core.database import SessionLocal
from app.core.db_models import JobModel, JobStatus, TranscriptionModel, TranscriptionSegmentModel
from app.core.shared_types import MediaFile

from ..data.whisper_adapter import WhisperAdapter

logger = logging.getLogger(__name__)

class TranscriptionHandler:
    def __init__(self):
        self.adapter = None 

    def _get_adapter(self, model_size: str):
        if not self.adapter or self.adapter.model_size != model_size:
            self.adapter = WhisperAdapter(model_size=model_size)
        return self.adapter

    def handle(self, job_id: UUID):
        logger.info(f"📝 Starting Transcription Job: {job_id}")
        
        with SessionLocal() as db:
            job = db.get(JobModel, job_id)
            if not job: raise ValueError(f"Job {job_id} not found")
            
            try:
                # 1. Prepare
                # Ensure path is a Path object for MediaFile
                audio_path = Path(job.source.original_file.file_path)
                model_size = job.payload.get("model_size", "large-v3")
                
                job.started_at = job.created_at
                job.status = JobStatus.PROCESSING
                db.commit()

                # 2. Transcribe
                adapter = self._get_adapter(model_size)
                result = adapter.transcribe(MediaFile(audio_path))
                
                # 3. Save Structured Data (The "Intelligence")
                transcription = TranscriptionModel(
                    source_id=job.source_id,
                    job_id=job.id,
                    language=result.language,
                    model_used=result.model_used,
                    full_text=result.full_text
                )
                
                # Create segments
                for seg in result.segments:
                    segment_record = TranscriptionSegmentModel(
                        start_time=seg.start_time,
                        end_time=seg.end_time,
                        text=seg.text
                    )
                    transcription.segments.append(segment_record)
                
                db.add(transcription)
                # Flush ensures we get IDs but allows rollback if commit fails later
                db.flush() 
                
                # 4. Update Job
                job.status = JobStatus.COMPLETED
                job.meta = {
                    "transcription_id": str(transcription.id),
                    "segment_count": len(result.segments),
                    "model_used": result.model_used
                }

                logger.info(f"✅ Transcription Success. Saved {len(result.segments)} segments.")
                
            except Exception as e:
                logger.error(f"❌ Transcription Failed: {e}")
                job.status = JobStatus.FAILED
                job.error_message = str(e)
            finally:
                db.commit()
