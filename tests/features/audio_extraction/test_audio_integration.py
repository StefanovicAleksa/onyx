import pytest
import subprocess
from pathlib import Path
from uuid import UUID

from app.core.database.connection import SessionLocal
from app.core.jobs.manager import JobManager
from app.core.jobs.models import JobModel, JobStatus
from app.core.jobs.types import JobType
from app.features.storage.service.api import storage
from app.features.storage.domain.models import IngestRequest
from app.features.storage.data.sql_models import SourceModel
from app.core.common.enums import SourceType
from app.features.audio_extraction.service.job_handler import AudioExtractionHandler
from app.features.audio_extraction.data.sql_models import VideoAudioModel

@pytest.fixture
def mock_video_file(tmp_path):
    video_path = tmp_path / "test_video.mp4"
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=1000:duration=1",
        "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p",
        str(video_path)
    ]
    subprocess.run(cmd, check=True)
    return video_path

def test_audio_extraction_pipeline(mock_video_file):
    # 1. Ingest Video
    ingest_req = IngestRequest(
        file_path=mock_video_file,
        source_name="Integration Test Video",
        source_type=SourceType.VIDEO_FILE
    )
    video_source_id = storage.ingest_file(ingest_req)

    # 2. Submit Extraction Job
    job_mgr = JobManager()
    job_id = job_mgr.submit_job(
        source_id=video_source_id,
        job_type=JobType.AUDIO_EXTRACTION,
        params={"bitrate": 128}
    )
    
    # 3. Execute Worker
    with SessionLocal() as db:
        job = db.get(JobModel, job_id)
        job.status = JobStatus.PROCESSING
        db.commit()

    handler = AudioExtractionHandler()
    result = handler.handle(video_source_id, {"bitrate": 128})
    
    # 4. Verify Results
    assert "audio_source_id" in result
    audio_source_id = UUID(result["audio_source_id"])
    
    with SessionLocal() as db:
        link = db.query(VideoAudioModel).filter_by(
            video_source_id=video_source_id,
            audio_source_id=audio_source_id
        ).first()
        assert link is not None