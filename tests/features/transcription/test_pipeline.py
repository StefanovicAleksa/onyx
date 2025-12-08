import pytest
import subprocess
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import Base
from app.core.db_models import JobModel, JobStatus
from app.core.enums import SourceType, JobType

from app.features.storage.service.api import ingest_file
from app.features.storage.domain.models import IngestRequest
from app.core.jobs.service.manager import JobManager
from app.core.jobs.domain.models import JobSubmission
from app.features.transcription.service.job_handler import TranscriptionHandler

# --- CONFIGURATION ---
TEST_ENGINE = create_engine(settings.DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)

@pytest.fixture(scope="function", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=TEST_ENGINE)
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)

@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def mock_audio_file(tmp_path):
    """
    Creates a tiny valid audio file for testing.
    Uses ffmpeg to generate silence/sine wave so Whisper doesn't crash on invalid input.
    """
    audio_path = tmp_path / "test_speech.mp3"
    # Generate 1 second of sine wave audio
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "sine=frequency=1000:duration=1",
        "-c:a", "libmp3lame", 
        str(audio_path)
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return audio_path

def test_transcription_job_execution(mock_audio_file, db_session):
    """
    Verifies that the Transcription Handler correctly:
    1. picks up a job
    2. runs the adapter
    3. saves the output to the DB
    """
    # 1. Ingest Audio
    req = IngestRequest(
        file_path=mock_audio_file, 
        source_name="Witness Tape 1", 
        source_type=SourceType.AUDIO_FILE
    )
    source_id = ingest_file(req)
    
    # 2. Submit Job (Using 'tiny' model for speed in tests)
    manager = JobManager()
    submission = JobSubmission(
        source_id=source_id,
        job_type=JobType.TRANSCRIPTION,
        payload={"model_size": "tiny"} 
    )
    job_id = manager.submit_job(submission)
    
    # 3. Execute Handler
    handler = TranscriptionHandler()
    handler.handle(job_id)
    
    # 4. Verify Database State
    job = db_session.get(JobModel, job_id)
    
    assert job.status == JobStatus.COMPLETED, f"Job failed: {job.error_message}"
    assert "full_text" in job.meta
    assert "segments" in job.meta
    assert job.meta["model_used"] == "tiny"
    
    print(f"\n✅ Transcription Job stored metadata: {job.meta.keys()}")
