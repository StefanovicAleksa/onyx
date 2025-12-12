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
from app.core.common.enums import SourceType

from app.features.transcription.service.job_handler import TranscriptionHandler
from app.features.transcription.data.sql_models import TranscriptionModel

# --- Setup Fixtures ---

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    """Reset DB for clean state"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def mock_audio_file(tmp_path):
    """Generates a small valid MP3 file using FFmpeg"""
    audio_path = tmp_path / "test_audio.mp3"
    # Generate 1 second of silence/sine wave
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=1000:duration=1",
        "-c:a", "libmp3lame", str(audio_path)
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return audio_path

# --- Tests ---

def test_transcription_pipeline(mock_audio_file):
    """
    Full integration test:
    1. Ingest File (Storage Feature)
    2. Submit Job (Core Feature)
    3. Run Job (Transcription Feature)
    4. Verify Database Records
    """
    
    # 1. Ingest
    print("\n[Test] Ingesting File...")
    ingest_req = IngestRequest(
        file_path=mock_audio_file,
        source_name="Integration Test Audio",
        source_type=SourceType.AUDIO_FILE
    )
    source_id = storage.ingest_file(ingest_req)
    assert isinstance(source_id, UUID)

    # 2. Submit Job
    print("[Test] Submitting Job...")
    job_mgr = JobManager()
    job_id = job_mgr.submit_job(
        source_id=source_id,
        job_type=JobType.TRANSCRIPTION,
        # Use 'tiny' model for speed in tests
        params={"model_size": "tiny"} 
    )
    
    # 3. Run Job (Simulate Worker)
    print("[Test] Running Worker...")
    # Set status to processing manually as the JobRunner usually does this
    with SessionLocal() as db:
        job = db.get(JobModel, job_id)
        job.status = JobStatus.PROCESSING
        db.commit()

    handler = TranscriptionHandler()
    result = handler.handle(source_id, {"model_size": "tiny"})
    
    # Mark complete
    with SessionLocal() as db:
        job = db.get(JobModel, job_id)
        job.status = JobStatus.COMPLETED
        job.result_meta = result
        db.commit()

    # 4. Verify
    print("[Test] Verifying Results...")
    assert result["segment_count"] >= 0 
    
    with SessionLocal() as db:
        # Check Transcription Table
        transcription = db.query(TranscriptionModel).filter_by(job_id=job_id).first()
        assert transcription is not None
        assert transcription.model_used == "tiny"
        assert transcription.source_id == source_id
        
        # Check Source Link
        assert transcription.source.name == "Integration Test Audio"
        
        print(f"[Success] Transcription ID: {transcription.id}")