# File: app/features/vad/service/job_handler.py
import logging
from uuid import UUID
from app.core.database.connection import SessionLocal
from app.core.jobs.models import JobModel, JobStatus
from app.features.storage.data.sql_models import SourceModel
from .api import run_vad_analysis

logger = logging.getLogger(__name__)

class VadHandler:
    """
    Worker class responsible for executing VAD_ANALYSIS jobs.
    Useful for 'Pre-flight' checks to see if a file has audio content
    before running heavier Transcription/Diarization jobs.
    """
    
    def handle(self, source_id: UUID, params: dict) -> dict:
        logger.info(f"Processing VAD Analysis for Source: {source_id}")

        with SessionLocal() as db:
            # 1. Resolve File Path
            source = db.get(SourceModel, source_id)
            if not source:
                raise ValueError(f"Source {source_id} not found.")
            
            file_record = source.original_file
            if not file_record:
                raise ValueError(f"Source {source_id} has no associated file.")
                
            audio_path = file_record.file_path

            # 2. Execute VAD (MarbleNet)
            # This calls the Adapter -> ModelOrchestrator
            segments = run_vad_analysis(audio_path)

            # 3. Serialize Results
            # We map the Domain Objects (VadSegment) to simple dicts
            result_payload = [
                {
                    "start": seg.start, 
                    "end": seg.end, 
                    "type": seg.event_type.value, # 'speech' or 'silence'
                    "conf": seg.confidence
                }
                for seg in segments
            ]
            
            # Calculate stats
            total_speech = sum(s.end - s.start for s in segments if s.event_type == "speech")
            total_silence = sum(s.end - s.start for s in segments if s.event_type == "silence")
            
            summary = {
                "total_duration": total_speech + total_silence,
                "speech_duration": total_speech,
                "silence_duration": total_silence,
                "ratio": total_speech / (total_speech + total_silence) if (total_speech + total_silence) > 0 else 0,
                "segments": result_payload
            }
            
            logger.info(f"VAD Complete. Speech Ratio: {summary['ratio']:.2f}")
            return summary