import pytest
import uuid
from app.core.database.connection import SessionLocal
from app.core.jobs.manager import JobManager
from app.core.jobs.types import JobType, JobStatus
from app.core.jobs.models import JobModel
from app.features.storage.data.sql_models import FileModel, SourceModel
from app.core.common.enums import FileType, SourceType

# REMOVED: @pytest.fixture def setup_db ... (This was dropping tables!)

def test_job_submission_flow():
    """
    Verifies that a job can be created and stored in the database.
    """
    # 1. SETUP: Create a valid Source first (Required by ForeignKey)
    with SessionLocal() as db:
        # Create Dummy File
        f = FileModel(
            file_path="/tmp/fake_job_test.wav",
            file_size_bytes=1024,
            file_hash="job_test_hash",
            file_type=FileType.AUDIO
        )
        db.add(f)
        db.flush()
        
        # Create Dummy Source
        s = SourceModel(
            name="Job Test Source",
            source_type=SourceType.AUDIO_FILE,
            file_id=f.id
        )
        db.add(s)
        db.commit()
        real_source_id = s.id

    # 2. EXECUTE: Submit Job
    manager = JobManager()
    job_id = manager.submit_job(
        source_id=real_source_id, 
        job_type=JobType.TRANSCRIPTION, 
        params={"model": "tiny"}
    )
    
    assert job_id is not None

    # 3. VERIFY
    with SessionLocal() as db:
        job = db.get(JobModel, job_id)
        assert job is not None
        assert job.source_id == real_source_id
        assert job.job_type == JobType.TRANSCRIPTION
        assert job.status == JobStatus.PENDING
        assert job.payload == {"model": "tiny"}

def test_run_job_routing_failure():
    """
    Verifies that running a job triggers the router.
    """
    manager = JobManager()
    
    # 1. SETUP: Create another valid Source
    with SessionLocal() as db:
        f = FileModel(
            file_path="/tmp/fail_test.wav",
            file_size_bytes=500,
            file_hash="fail_test_hash",
            file_type=FileType.AUDIO
        )
        db.add(f)
        db.flush()
        s = SourceModel(
            name="Fail Test Source",
            source_type=SourceType.AUDIO_FILE,
            file_id=f.id
        )
        db.add(s)
        db.commit()
        real_source_id = s.id

    # 2. EXECUTE: Submit a job type that has no handler
    job_id = manager.submit_job(
        source_id=real_source_id, 
        job_type=JobType.INTELLIGENCE
    )
    
    # Run it
    manager.run_job(job_id)
    
    # 3. VERIFY
    with SessionLocal() as db:
        job = db.get(JobModel, job_id)
        assert job.status == JobStatus.FAILED
        assert "No handler registered" in job.error_message