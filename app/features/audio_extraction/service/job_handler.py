import logging
from pathlib import Path
from uuid import UUID

from app.core.database import SessionLocal
from app.core.db_models import JobModel, JobStatus
from app.core.enums import SourceType
from app.core.shared_types import MediaFile

from app.features.storage.service.api import ingest_file
from app.features.storage.domain.models import IngestRequest

from ..domain.models import AudioExtractionTask
from ..data.ffmpeg_adapter import FFmpegAudioAdapter

logger = logging.getLogger(__name__)

class AudioExtractionHandler:
    """
    Worker logic that executes an AUDIO_EXTRACTION job.
    """
    
    def __init__(self):
        self.adapter = FFmpegAudioAdapter()

    def handle(self, job_id: UUID):
        """
        Orchestrates the extraction process:
        1. Fetch Job & Source File
        2. Run FFmpeg
        3. Ingest Resulting MP3
        4. Update Job
        """
        logger.info(f"🎧 Starting Audio Extraction Job: {job_id}")
        
        with SessionLocal() as db:
            job = db.get(JobModel, job_id)
            if not job:
                raise ValueError(f"Job {job_id} not found")
            
            # Initialize temp_output to None to handle scope in finally/except blocks safely
            temp_output = None
            
            try:
                # 1. Prepare Paths
                # The Source points to the raw video file
                video_path = Path(job.source.original_file.file_path)
                
                # Create a temp path for the output
                # (The Storage feature will move it to the final location later)
                temp_output = video_path.parent / f"{video_path.stem}_extracted.mp3"
                
                # 2. Update Job to Processing
                job.started_at = job.created_at # In real worker, use utc_now()
                job.status = JobStatus.PROCESSING
                db.commit()

                # 3. Execute Domain Logic
                task = AudioExtractionTask(
                    source_video=MediaFile(video_path),
                    output_audio=MediaFile(temp_output),
                    bitrate_kbps=job.payload.get("bitrate", 192)
                )
                
                self.adapter.extract(task)
                
                # 4. Ingest the Resulting MP3 into Storage
                # This ensures the MP3 is deduped and managed like any other file
                ingest_req = IngestRequest(
                    file_path=temp_output,
                    source_name=f"Audio Extraction - {job.source.name}",
                    source_type=SourceType.AUDIO_FILE
                )
                
                # This moves the file to /artifacts and creates a DB record
                mp3_source_id = ingest_file(ingest_req)
                
                # 5. Success: Link the result to the job
                job.status = JobStatus.COMPLETED
                job.meta = {
                    "output_source_id": str(mp3_source_id),
                    "original_filename": video_path.name
                }
                
                logger.info(f"✅ Job {job_id} Success. Created Source: {mp3_source_id}")
                
            except Exception as e:
                logger.error(f"❌ Job {job_id} Failed: {e}")
                job.status = JobStatus.FAILED
                job.error_message = str(e)
                # Ensure temp file is cleaned up on failure
                if temp_output and temp_output.exists():
                    temp_output.unlink()
            finally:
                db.commit()
