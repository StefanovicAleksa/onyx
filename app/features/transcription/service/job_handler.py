# File: app/features/transcription/service/job_handler.py
import logging
from uuid import UUID
from app.core.database.connection import SessionLocal
from app.core.jobs.models import JobModel, JobStatus
from app.features.storage.data.sql_models import SourceModel
from ..data.whisper_adapter import WhisperAdapter
from ..data.sql_models import TranscriptionModel, TranscriptionSegmentModel

logger = logging.getLogger(__name__)

class TranscriptionHandler:
    """
    Worker class responsible for executing TRANSCRIPTION jobs.
    Updated to save Rich Metadata to DB.
    """
    
    def handle(self, source_id: UUID, params: dict) -> dict:
        logger.info(f"Processing Transcription for Source: {source_id}")

        with SessionLocal() as db:
            # 1. Resolve File Path
            source = db.get(SourceModel, source_id)
            if not source:
                raise ValueError(f"Source {source_id} not found.")
            
            file_record = source.original_file
            if not file_record:
                raise ValueError(f"Source {source_id} has no associated file.")
                
            audio_path = file_record.file_path
            model_size = params.get("model_size", "base")

            # 2. Execute Transcription
            adapter = WhisperAdapter()
            result = adapter.transcribe(audio_path, model_size)

            # 3. Retrieve the Job ID
            job = db.query(JobModel).filter(
                JobModel.source_id == source_id,
                JobModel.status == JobStatus.PROCESSING
            ).first()
            job_id_val = job.id if job else None
            
            if not job_id_val:
                logger.warning("No active JOB found for this transcription.")
                # If rigorous, create dummy job or raise error. 
                # For now, we proceed to allow testing.

            # 4. Save Header
            transcription = TranscriptionModel(
                source_id=source.id,
                job_id=job_id_val,
                language=result.language,
                model_used=result.model_used,
                full_text=result.full_text,
                processing_meta=result.processing_meta
            )
            
            db.add(transcription)
            db.flush() 

            # 5. Save Segments with Rich Metadata
            for seg in result.segments:
                
                # Serialize the domain objects to JSON dicts
                meta_payload = {
                    "confidence": seg.confidence,
                    "words": [
                        {"w": w.word, "s": w.start, "e": w.end, "c": w.confidence} 
                        for w in seg.words
                    ],
                    "raw_meta": seg.metadata
                }

                db.add(TranscriptionSegmentModel(
                    transcription_id=transcription.id,
                    start_time=seg.start,
                    end_time=seg.end,
                    text=seg.text,
                    # speaker_id remains NULL until Pipeline feature is built
                    meta_data=meta_payload
                ))

            db.commit()
            
            logger.info(f"Transcription saved. ID: {transcription.id}, Segments: {len(result.segments)}")
            
            return {
                "transcription_id": str(transcription.id),
                "segment_count": len(result.segments),
                "language": result.language
            }