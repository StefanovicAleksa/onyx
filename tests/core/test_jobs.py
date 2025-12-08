import pytest
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

# --- CONFIGURATION ---
TEST_ENGINE = create_engine(settings.DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)

# --- FIXTURES ---

@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """
    Reset DB for each test to ensure clean state.
    """
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
def temp_file(tmp_path):
    p = tmp_path / "contract_draft.txt"
    p.write_text("This is a legal contract.")
    return p

# --- TESTS ---

def test_smart_deduplication(temp_file, db_session):
    """
    Scenario:
    1. User uploads File A as 'Source A'.
    2. User runs Transcription on Source A. It finishes.
    3. User uploads File A again as 'Source B'.
    4. User runs Transcription on Source B.
    
    Expected:
    - System detects File A == File B.
    - System sees Transcription is already done for File A.
    - System instantly marks Source B's job as COMPLETED and copies the result.
    """
    
    # ---------------------------------------------------------
    # STEP 1: Ingest Source A & Source B (Same Physical File)
    # ---------------------------------------------------------
    
    # Source A
    req_a = IngestRequest(file_path=temp_file, source_name="Source A", source_type=SourceType.DOCUMENT)
    source_id_a = ingest_file(req_a)
    
    # Source B (Need to recreate file because ingest moves/deletes the original)
    file_b = temp_file.parent / "contract_final.txt"
    file_b.write_text("This is a legal contract.") # Identical content
    
    req_b = IngestRequest(file_path=file_b, source_name="Source B", source_type=SourceType.DOCUMENT)
    source_id_b = ingest_file(req_b)
    
    assert source_id_a != source_id_b
    
    # ---------------------------------------------------------
    # STEP 2: Run Job on Source A (The "Original" Compute)
    # ---------------------------------------------------------
    
    manager = JobManager()
    
    submission_a = JobSubmission(
        source_id=source_id_a,
        job_type=JobType.TRANSCRIPTION,
        payload={"model": "whisper-large"}
    )
    
    job_id_a = manager.submit_job(submission_a)
    
    # Verify it is PENDING (Cache Miss)
    job_a = db_session.get(JobModel, job_id_a)
    assert job_a.status == JobStatus.PENDING
    
    # SIMULATE WORKER: Manually complete Job A
    job_a.status = JobStatus.COMPLETED
    job_a.meta = {"transcript": "This is a legal contract.", "confidence": 0.99}
    db_session.commit()
    
    # ---------------------------------------------------------
    # STEP 3: Run Job on Source B (The "Smart" Clone)
    # ---------------------------------------------------------
    
    submission_b = JobSubmission(
        source_id=source_id_b,
        job_type=JobType.TRANSCRIPTION,
        payload={"model": "whisper-large"} # Exact same config
    )
    
    job_id_b = manager.submit_job(submission_b)
    
    # ---------------------------------------------------------
    # STEP 4: Assertions
    # ---------------------------------------------------------
    
    job_b = db_session.get(JobModel, job_id_b)
    
    # 1. It should be a DIFFERENT Job ID (we track them separately)
    assert job_id_a != job_id_b
    
    # 2. It should be COMPLETED immediately
    assert job_b.status == JobStatus.COMPLETED
    
    # 3. It should have COPIED the metadata (Transcript) from Job A
    assert job_b.meta["transcript"] == "This is a legal contract."
    assert job_b.meta["confidence"] == 0.99
    
    print(f"\n✅ Smart Deduplication Success: Job {job_id_b} reused result from Job {job_id_a}")
