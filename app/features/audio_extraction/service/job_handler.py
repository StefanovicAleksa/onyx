import logging
from pathlib import Path
from uuid import UUID
from app.core.database import SessionLocal
from app.core.db_models import JobModel, JobStatus, VideoAudioModel, SourceModel
from app.core.enums import SourceType
from app.core.shared_types import MediaFile
from app.features.storage.service.api import ingest_file
from app.features.storage.domain.models import IngestRequest
from ..domain.models import AudioExtractionTask
from ..data.ffmpeg_adapter import FFmpegAudioAdapter

logger = logging.getLogger(__name__)

class AudioExtractionHandler:
    def __init__(self): self.adapter = FFmpegAudioAdapter()

    def handle(self, job_id: UUID):
        logger.info(f"🎧 Starting Audio Extraction Job: {job_id}")
        with SessionLocal() as db:
            job = db.get(JobModel, job_id)
            temp_output = None
            try:
                video_path = Path(job.source.original_file.file_path)
                temp_output = video_path.parent / f"{video_path.stem}_extracted.mp3"
                job.status = JobStatus.PROCESSING
                db.commit()

                task = AudioExtractionTask(MediaFile(video_path), MediaFile(temp_output), job.payload.get("bitrate", 192))
                self.adapter.extract(task)
                
                mp3_source_id = ingest_file(IngestRequest(temp_output, f"Audio - {job.source.name}", SourceType.AUDIO_FILE))
                
                mp3_source = db.get(SourceModel, mp3_source_id)
                db.add(VideoAudioModel(source_id=job.source_id, audio_file_id=mp3_source.file_id))

                job.status = JobStatus.COMPLETED
                job.meta = { "output_source_id": str(mp3_source_id) }
                logger.info(f"✅ Job {job_id} Success.")
            except Exception as e:
                logger.error(f"❌ Job {job_id} Failed: {e}")
                job.status = JobStatus.FAILED
                job.error_message = str(e)
                if temp_output and temp_output.exists(): temp_output.unlink()
            finally: db.commit()
