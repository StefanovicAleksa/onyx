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
    """
    
    def handle(self, source_id: UUID, params: dict) -> dict:
        """
        1. Retrieves file path from Source ID.
        2. Runs Whisper (via Adapter).
        3. Saves Transcription and Segments to DB.
        """
        logger.info(f"Processing Transcription for Source: {source_id}")

        with SessionLocal() as db:
            # 1. Resolve File Path
            source = db.get(SourceModel, source_id)
            if not source:
                raise ValueError(f"Source {source_id} not found.")
            
            # The Source points to a File record which has the path
            file_record = source.original_file
            if not file_record:
                raise ValueError(f"Source {source_id} has no associated file.")
                
            audio_path = file_record.file_path
            model_size = params.get("model_size", "base") # Default to base for speed if not specified

            # 2. Execute Transcription
            adapter = WhisperAdapter()
            result = adapter.transcribe(audio_path, model_size)

            # 3. Retrieve the Job ID
            # (In a real queue system, job_id is passed in. Here we find the running job).
            job = db.query(JobModel).filter(
                JobModel.source_id == source_id,
                JobModel.status == JobStatus.PROCESSING
            ).first()
            
            # Fallback for direct execution without job context
            job_id_val = job.id if job else None
            
            if not job_id_val:
                # If we are running this manually outside the job manager, we skip DB link or create dummy
                logger.warning("No active JOB found for this transcription. saving with null job_id might fail constraint.")
                # For safety in this strict schema, we assume a job exists. 
                # If testing manually, ensure a job is created first.

            # 4. Save Header
            transcription = TranscriptionModel(
                source_id=source.id,
                job_id=job_id_val,
                language=result.language,
                model_used=result.model_used,
                full_text=result.full_text
            )
            db.add(transcription)
            db.flush() # Generate ID

            # 5. Save Segments (Bulk insert is better, but loop is fine for now)
            for seg in result.segments:
                db.add(TranscriptionSegmentModel(
                    transcription_id=transcription.id,
                    start_time=seg.start,
                    end_time=seg.end,
                    text=seg.text
                ))

            db.commit()
            
            logger.info(f"Transcription saved. ID: {transcription.id}, Segments: {len(result.segments)}")
            
            return {
                "transcription_id": str(transcription.id),
                "segment_count": len(result.segments),
                "language": result.language
            }