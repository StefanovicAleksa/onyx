import pytest
import subprocess
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import Base
from app.core.db_models import JobModel, JobStatus, TranscriptionModel, TranscriptionSegmentModel
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
    try: yield session
    finally: session.close()

@pytest.fixture
def mock_audio_file(tmp_path):
    """
    Creates a tiny valid audio file for testing.
    """
    audio_path = tmp_path / "test_speech.mp3"
    # Generate 1 sec sine wave
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "sine=frequency=1000:duration=1",
        "-c:a", "libmp3lame", 
        str(audio_path)
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return audio_path

def test_transcription_persistence(mock_audio_file, db_session):
    """
    Verifies that we are actually saving rows to the Transcription tables,
    not just JSON in the Job table.
    """
    # 1. Ingest
    sid = ingest_file(IngestRequest(mock_audio_file, "Audio", SourceType.AUDIO_FILE))
    
    # 2. Submit
    jid = JobManager().submit_job(JobSubmission(sid, JobType.TRANSCRIPTION, {"model_size": "tiny"}))
    
    # 3. Handle
    TranscriptionHandler().handle(jid)
    
    # 4. Verify DB
    job = db_session.get(JobModel, jid)
    assert job.status == JobStatus.COMPLETED
    
    # Check Transcription Table
    transcription = db_session.query(TranscriptionModel).filter_by(job_id=jid).first()
    assert transcription is not None
    assert transcription.full_text is not None
    
    # Check Metadata Link
    assert job.meta["transcription_id"] == str(transcription.id)
    
    print(f"\n✅ Transcription Data Verified. ID: {transcription.id}")
