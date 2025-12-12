import logging
import tempfile
from uuid import UUID
from pathlib import Path

from app.core.database.connection import SessionLocal
from app.features.storage.data.sql_models import SourceModel
from app.features.storage.service.api import storage
from app.features.storage.domain.models import IngestRequest
from app.core.common.enums import SourceType

from ..data.ffmpeg_adapter import FFmpegAdapter
from ..data.sql_models import VideoAudioModel
from ..domain.models import ExtractionConfig

logger = logging.getLogger(__name__)

class AudioExtractionHandler:
    """
    Worker for JOB_TYPE.AUDIO_EXTRACTION.
    """
    
    def handle(self, source_id: UUID, params: dict) -> dict:
        logger.info(f"Processing Audio Extraction for Source: {source_id}")
        
        with SessionLocal() as db:
            # 1. Fetch Video Source
            video_source = db.get(SourceModel, source_id)
            if not video_source:
                raise ValueError(f"Source {source_id} not found.")
            
            # The original file path
            video_path = Path(video_source.original_file.file_path)
            
            # 2. Extract to Temp
            # We assume Storage service handles the final move to artifacts
            with tempfile.TemporaryDirectory() as tmp_dir:
                adapter = FFmpegAdapter()
                config = ExtractionConfig(
                    bitrate_kbps=params.get("bitrate", 192)
                )
                
                # Perform Extraction
                result = adapter.extract_audio(video_path, Path(tmp_dir), config)
                
                # 3. Ingest the Result as a new Source
                # This creates a NEW FileModel and SourceModel for the .mp3
                audio_source_name = f"Audio - {video_source.name}"
                
                ingest_req = IngestRequest(
                    file_path=result.output_path,
                    source_name=audio_source_name,
                    source_type=SourceType.AUDIO_FILE
                )
                
                audio_source_id = storage.ingest_file(ingest_req)
                
            # 4. Create the Link (Video -> Audio) in DB
            # First check if link exists to be safe
            existing_link = db.query(VideoAudioModel).filter_by(
                video_source_id=video_source.id,
                audio_source_id=audio_source_id
            ).first()
            
            if not existing_link:
                link = VideoAudioModel(
                    video_source_id=video_source.id,
                    audio_source_id=audio_source_id
                )
                db.add(link)
                db.commit()
                
            logger.info(f"Linked Video {source_id} to Audio {audio_source_id}")
            
            return {
                "audio_source_id": str(audio_source_id),
                "format": result.format
            }