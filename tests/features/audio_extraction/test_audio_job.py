import pytest
import subprocess
from app.core.database import Base
from app.core.db_models import JobModel, JobStatus, VideoAudioModel
from app.core.enums import SourceType, JobType
from app.features.storage.service.api import ingest_file
from app.features.storage.domain.models import IngestRequest
from app.core.jobs.service.manager import JobManager
from app.core.jobs.domain.models import JobSubmission
from app.features.audio_extraction.service.job_handler import AudioExtractionHandler
from tests.conftest import TEST_ENGINE, TestingSessionLocal

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

def test_audio_link(tmp_path, db_session):
    p = tmp_path / "vid.mp4"
    # FIX: Added '-f lavfi -i sine=f=1000:d=1' to generate dummy audio!
    # -map 0:v -map 1:a ensures we map video from input 0 and audio from input 1
    subprocess.run([
        "ffmpeg", "-y", 
        "-f", "lavfi", "-i", "testsrc=d=1", 
        "-f", "lavfi", "-i", "sine=f=1000:d=1",
        "-c:v", "libx264", "-c:a", "aac", 
        "-map", "0:v", "-map", "1:a",
        str(p)
    ], check=True, capture_output=True)
    
    sid = ingest_file(IngestRequest(p, "Vid", SourceType.VIDEO_FILE))
    jid = JobManager().submit_job(JobSubmission(sid, JobType.AUDIO_EXTRACTION, {}))
    
    AudioExtractionHandler().handle(jid)
    
    link = db_session.query(VideoAudioModel).filter_by(source_id=sid).first()
    assert link is not None
