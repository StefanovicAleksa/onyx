import logging
from uuid import UUID
from app.core.database.connection import SessionLocal
from app.features.storage.data.sql_models import SourceModel
from .api import detect_voice_activity

logger = logging.getLogger(__name__)

class VadHandler:
    """
    Worker class responsible for executing VAD_ANALYSIS jobs.
    This runs Marblenet to find speech timestamps.
    """
    
    def handle(self, source_id: UUID, params: dict) -> dict:
        logger.info(f"Processing VAD for Source: {source_id}")
        
        with SessionLocal() as db:
            # 1. Resolve File Path from DB
            source = db.get(SourceModel, source_id)
            if not source:
                raise ValueError(f"Source {source_id} not found")
            
            # The Source points to a File record which has the path
            file_record = source.original_file
            if not file_record:
                raise ValueError(f"Source {source_id} has no associated file.")
                
            audio_path = file_record.file_path
            
            # 2. Execute VAD Service
            # (The service handles the GPU locking via Orchestrator)
            segments = detect_voice_activity(audio_path)
            
            # 3. Calculate Stats
            total_speech_duration = sum([s.duration for s in segments])
            
            # 4. Result
            # For VAD, we often just want the metadata or the raw segments 
            # to pass to the next step (Transcription).
            # We return them in the result_meta so the Job Manager can store them.
            return {
                "speech_segments_found": len(segments),
                "total_speech_seconds": total_speech_duration,
                "segments": [
                    {"start": s.start, "end": s.end, "conf": s.confidence} 
                    for s in segments
                ]
            }