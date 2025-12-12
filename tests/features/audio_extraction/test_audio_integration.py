import pytest
import subprocess
from pathlib import Path
from uuid import UUID

from app.core.database.base import Base
from app.core.database.connection import engine, SessionLocal
from app.core.jobs.manager import JobManager
from app.core.jobs.models import JobModel, JobStatus
from app.core.jobs.types import JobType

from app.features.storage.service.api import storage
from app.features.storage.domain.models import IngestRequest
from app.features.storage.data.sql_models import SourceModel
from app.core.common.enums import SourceType

from app.features.audio_extraction.service.job_handler import AudioExtractionHandler
from app.features.audio_extraction.data.sql_models import VideoAudioModel

# --- Fixtures ---

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    """Reset DB for clean state"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def mock_video_file(tmp_path):
    """
    Generates a small valid MP4 file with audio using FFmpeg.
    We need actual video/audio streams for the extractor to work.
    """
    video_path = tmp_path / "test_video.mp4"
    
    # Generate 1 second of video (testsrc) + audio (sine wave)
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=1000:duration=1",
        "-c:v", "libx264", # Video Codec
        "-c:a", "aac",     # Audio Codec
        "-pix_fmt", "yuv420p",
        str(video_path)
    ]
    
    # Suppress output unless error
    subprocess.run(cmd, check=True, capture_output=True)
    return video_path

# --- Integration Test ---

def test_audio_extraction_pipeline(mock_video_file):
    """
    Verifies:
    1. Video Ingestion.
    2. Job Submission.
    3. Audio Extraction (Worker execution).
    4. Creation of new Audio Source.
    5. Database Link (Video -> Audio).
    """
    
    # 1. Ingest Video
    print(f"\n[Test] Ingesting Video: {mock_video_file}...")
    ingest_req = IngestRequest(
        file_path=mock_video_file,
        source_name="Integration Test Video",
        source_type=SourceType.VIDEO_FILE
    )
    video_source_id = storage.ingest_file(ingest_req)
    assert isinstance(video_source_id, UUID)

    # 2. Submit Extraction Job
    print("[Test] Submitting Extraction Job...")
    job_mgr = JobManager()
    job_id = job_mgr.submit_job(
        source_id=video_source_id,
        job_type=JobType.AUDIO_EXTRACTION,
        params={"bitrate": 128}
    )
    
    # 3. Execute Worker (Simulate Background Task)
    print("[Test] Running Extraction Worker...")
    
    # Update Job Status (Simulating Job Runner)
    with SessionLocal() as db:
        job = db.get(JobModel, job_id)
        job.status = JobStatus.PROCESSING
        db.commit()

    # Run Handler
    handler = AudioExtractionHandler()
    result = handler.handle(video_source_id, {"bitrate": 128})
    
    # Mark Complete
    with SessionLocal() as db:
        job = db.get(JobModel, job_id)
        job.status = JobStatus.COMPLETED
        job.result_meta = result
        db.commit()

    # 4. Verify Results
    print("[Test] Verifying Database Records...")
    
    assert "audio_source_id" in result
    audio_source_id = UUID(result["audio_source_id"])
    
    with SessionLocal() as db:
        # A. Check Link Table
        link = db.query(VideoAudioModel).filter_by(
            video_source_id=video_source_id,
            audio_source_id=audio_source_id
        ).first()
        
        assert link is not None, "VideoAudio link was not created"
        
        # B. Check New Audio Source
        audio_source = db.get(SourceModel, audio_source_id)
        assert audio_source is not None
        assert audio_source.source_type == SourceType.AUDIO_FILE
        assert "Audio -" in audio_source.name
        
        # C. Verify Physical File
        audio_file_record = audio_source.original_file
        audio_path = Path(audio_file_record.file_path)
        
        assert audio_path.exists(), "Extracted audio file missing from disk"
        assert audio_path.suffix == ".mp3"
        assert audio_file_record.file_size_bytes > 0
        
        print(f"[Success] Extracted Audio: {audio_path}")