import pytest
import subprocess
from pathlib import Path
from app.core.database.connection import SessionLocal
from app.core.jobs.manager import JobManager
from app.core.jobs.models import JobModel, JobStatus
from app.core.jobs.types import JobType
from app.features.storage.service.api import storage
from app.features.storage.domain.models import IngestRequest
from app.core.common.enums import SourceType
from app.features.vad.service.job_handler import VadHandler

@pytest.fixture
def mock_speech_file(tmp_path):
    """Restored Fixture: Creates a fake audio file for testing."""
    audio_path = tmp_path / "vad_real_test.wav"
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", "sine=frequency=400:duration=4",
        "-af", "volume=enable='between(t,0,1)':volume=0, volume=enable='between(t,3,4)':volume=0",
        str(audio_path)
    ]
    subprocess.run(cmd, check=True)
    return audio_path

def test_vad_pipeline_execution(mock_speech_file):
    # 1. Ingest
    ingest_req = IngestRequest(
        file_path=mock_speech_file,
        source_name="VAD Test Audio",
        source_type=SourceType.AUDIO_FILE
    )
    source_id = storage.ingest_file(ingest_req)
    
    # 2. Submit Job
    job_mgr = JobManager()
    job_id = job_mgr.submit_job(source_id=source_id, job_type=JobType.VAD_ANALYSIS)
    
    # 3. Simulate Worker Pickup
    with SessionLocal() as db:
        job = db.get(JobModel, job_id)
        job.status = JobStatus.PROCESSING
        db.commit()

    # 4. Run Handler
    handler = VadHandler()
    result = handler.handle(source_id, {})
    
    # 5. Verify
    assert "speech_segments_found" in result
    assert "total_speech_seconds" in result
    assert isinstance(result["segments"], list)