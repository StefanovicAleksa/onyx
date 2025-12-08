import pytest
import subprocess
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import Base
from app.core.db_models import JobModel, JobStatus, VideoAudioModel
from app.core.enums import SourceType, JobType

from app.features.storage.service.api import ingest_file
from app.features.storage.domain.models import IngestRequest
from app.core.jobs.service.manager import JobManager
from app.core.jobs.domain.models import JobSubmission

from app.features.audio_extraction.service.job_handler import AudioExtractionHandler
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
def fake_video_file(tmp_path):
    """
    Generates a valid MP4 file containing a sine wave audio track.
    We use a specific frequency so we can't check the text content accurately (it's just beeps),
    but we CAN check that the pipeline successfully processed it all the way through.
    """
    video_path = tmp_path / "interview_footage.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=30", # Visuals
        "-f", "lavfi", "-i", "sine=frequency=1000:duration=1",          # Audio
        "-c:v", "libx264", "-c:a", "aac", 
        str(video_path)
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return video_path

def test_full_video_to_text_pipeline(fake_video_file, db_session):
    """
    THE MASTER TEST:
    Video -> Ingest -> Extract Audio Job -> Link Audio -> Transcribe Job -> Final Result
    """
    job_manager = JobManager()
    audio_worker = AudioExtractionHandler()
    transcription_worker = TranscriptionHandler()

    print("\n🎬 Step 1: Ingesting Video...")
    video_req = IngestRequest(
        file_path=fake_video_file,
        source_name="End-to-End Test Video",
        source_type=SourceType.VIDEO_FILE
    )
    video_source_id = ingest_file(video_req)
    assert video_source_id is not None

    print("🎧 Step 2: Submitting Audio Extraction Job...")
    submission_1 = JobSubmission(
        source_id=video_source_id,
        job_type=JobType.AUDIO_EXTRACTION,
        payload={"bitrate": 128}
    )
    job_id_1 = job_manager.submit_job(submission_1)
    
    # RUN WORKER 1
    audio_worker.handle(job_id_1)
    
    # Verify Job 1 Success
    job_1 = db_session.get(JobModel, job_id_1)
    assert job_1.status == JobStatus.COMPLETED
    
    print("🔗 Step 3: Finding Linked Audio Source...")
    # The worker should have created a link in VideoAudioModel
    link = db_session.query(VideoAudioModel).filter_by(source_id=video_source_id).first()
    assert link is not None, "Audio extraction failed to link output to input"
    
    # We need the Source ID of the *Audio File* to submit the next job
    # We can find it by looking up the Source that points to this audio_file_id
    # (In a real app, we'd probably query the Source table directly via the file_id)
    audio_source = link.source # This is the Video Source, wait.
    
    # Correction: The VideoAudioModel links Source(Video) -> File(Audio).
    # We need to find the Source record for that Audio File to submit a job on it.
    # The worker creates a source named "Audio Extraction - ..."
    from app.core.db_models import SourceModel
    audio_source_record = db_session.query(SourceModel).filter_by(file_id=link.audio_file_id).first()
    assert audio_source_record is not None
    
    print(f"📝 Step 4: Submitting Transcription Job for Source {audio_source_record.id}...")
    submission_2 = JobSubmission(
        source_id=audio_source_record.id,
        job_type=JobType.TRANSCRIPTION,
        payload={"model_size": "tiny"}
    )
    job_id_2 = job_manager.submit_job(submission_2)
    
    # RUN WORKER 2
    transcription_worker.handle(job_id_2)
    
    # Verify Job 2 Success
    job_2 = db_session.get(JobModel, job_id_2)
    assert job_2.status == JobStatus.COMPLETED
    
    print("✅ Step 5: Verifying Final Transcript Metadata...")
    meta = job_2.meta
    assert "full_text" in meta
    assert "segments" in meta
    assert meta["model_used"] == "tiny"
    
    print(f"🎉 SUCCESS! Full pipeline executed. Transcript length: {len(meta['full_text'])}")
