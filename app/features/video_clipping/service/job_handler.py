import logging
import tempfile
from uuid import UUID
from pathlib import Path

from app.core.database.connection import SessionLocal
from app.features.storage.data.sql_models import SourceModel
from app.features.storage.service.api import storage
from app.features.storage.domain.models import IngestRequest
from app.core.common.enums import SourceType

from ..data.ffmpeg_adapter import FFmpegClipAdapter
from ..data.sql_models import VideoClipModel
from ..domain.models import ClipRequest, TimeRange, MediaFile

logger = logging.getLogger(__name__)

class VideoClippingHandler:
    """
    Worker for JOB_TYPE.VIDEO_CLIPPING.
    """
    
    def handle(self, source_id: UUID, params: dict) -> dict:
        start_time = float(params.get("start", 0.0))
        end_time = float(params.get("end", 0.0))
        
        if end_time <= start_time:
            raise ValueError(f"Invalid clip duration: {start_time} to {end_time}")

        logger.info(f"Processing Clip for Source {source_id} ({start_time}-{end_time}s)")
        
        with SessionLocal() as db:
            # 1. Get Original Video
            parent_source = db.get(SourceModel, source_id)
            if not parent_source:
                raise ValueError(f"Source {source_id} not found")
                
            original_path = Path(parent_source.original_file.file_path)
            
            # 2. Generate Clip in Temp
            with tempfile.TemporaryDirectory() as tmp_dir:
                adapter = FFmpegClipAdapter()
                
                # Naming: original_clip_10_20.mp4
                output_filename = f"{original_path.stem}_clip_{int(start_time)}_{int(end_time)}.mp4"
                temp_output_path = Path(tmp_dir) / output_filename
                
                # UPDATED: Use MediaFile wrappers and correct field names
                request = ClipRequest(
                    source_video=MediaFile(original_path, validate_exists=True),
                    output_video=MediaFile(temp_output_path, validate_exists=False),
                    time_range=TimeRange(start_time, end_time)
                )
                
                adapter.create_clip(request)
                
                # 3. Ingest Result as New Source
                clip_source_name = f"Clip {start_time}-{end_time}s: {parent_source.name}"
                
                ingest_req = IngestRequest(
                    file_path=temp_output_path,
                    source_name=clip_source_name,
                    source_type=SourceType.VIDEO_FILE
                )
                
                # Moves file to artifacts
                clip_source_id = storage.ingest_file(ingest_req)
                
            # 4. Save Lineage (The "Missing" Step)
            # This allows us to trace back where this clip came from.
            clip_record = VideoClipModel(
                parent_source_id=parent_source.id,
                clip_source_id=clip_source_id,
                start_time_seconds=start_time,
                end_time_seconds=end_time
            )
            db.add(clip_record)
            db.commit()
            
            logger.info(f"Clip Source {clip_source_id} created from Parent {source_id}")
            
            return {
                "clip_source_id": str(clip_source_id),
                "duration": end_time - start_time,
                "lineage_id": str(clip_record.id)
            }