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

from app.features.video_clipping.service.job_handler import VideoClippingHandler

# --- Fixtures ---

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def mock_video_file(tmp_path):
    """
    Generates a 5-second video file with a counter.
    """
    video_path = tmp_path / "clip_source.mp4"
    
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=5:size=320x240:rate=30",
        "-c:v", "libx264",
        str(video_path)
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return video_path

# --- Tests ---

def test_video_clipping_pipeline(mock_video_file):
    """
    1. Ingest 5s video.
    2. Submit Clip Job (1s - 3s).
    3. Run Handler.
    4. Verify new Source is ~2s long.
    """
    
    # 1. Ingest
    print(f"\n[Test] Ingesting Video...")
    ingest_req = IngestRequest(
        file_path=mock_video_file,
        source_name="Long Video",
        source_type=SourceType.VIDEO_FILE
    )
    parent_source_id = storage.ingest_file(ingest_req)

    # 2. Submit Job
    print("[Test] Submitting Clipping Job...")
    job_mgr = JobManager()
    job_id = job_mgr.submit_job(
        source_id=parent_source_id,
        job_type=JobType.VIDEO_CLIPPING,
        params={"start": 1.0, "end": 3.0}
    )

    # 3. Execute Handler
    print("[Test] Running Clipping Worker...")
    with SessionLocal() as db:
        job = db.get(JobModel, job_id)
        job.status = JobStatus.PROCESSING
        db.commit()

    handler = VideoClippingHandler()
    result = handler.handle(parent_source_id, {"start": 1.0, "end": 3.0})

    # Mark Complete
    with SessionLocal() as db:
        job = db.get(JobModel, job_id)
        job.status = JobStatus.COMPLETED
        job.result_meta = result
        db.commit()

    # 4. Verify
    print(f"[Test] Result: {result}")
    
    clip_source_id = UUID(result["clip_source_id"])
    assert clip_source_id != parent_source_id
    
    with SessionLocal() as db:
        # Check Database Entry
        clip_source = db.get(SourceModel, clip_source_id)
        assert clip_source is not None
        assert "Clip" in clip_source.name
        
        # Check Physical File
        clip_file_rec = clip_source.original_file
        clip_path = Path(clip_file_rec.file_path)
        assert clip_path.exists()
        
        # Verify Duration using ffprobe
        # We expect roughly 2.0 seconds
        probe_cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration", 
            "-of", "default=noprint_wrappers=1:nokey=1", str(clip_path)
        ]
        probe_res = subprocess.run(probe_cmd, capture_output=True, text=True)
        actual_duration = float(probe_res.stdout.strip())
        
        print(f"‚úÖ Actual Clip Duration: {actual_duration}s")
        assert 1.9 <= actual_duration <= 2.1