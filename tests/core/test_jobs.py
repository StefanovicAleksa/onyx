import pytest
from app.core.database import Base
from app.core.db_models import JobModel, JobStatus
from app.core.enums import SourceType, JobType
from app.features.storage.service.api import ingest_file
from app.features.storage.domain.models import IngestRequest
from app.core.jobs.service.manager import JobManager
from app.core.jobs.domain.models import JobSubmission
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

def test_smart_deduplication(tmp_path, db_session):
    f1 = tmp_path / "doc.txt"
    f1.write_text("content")
    id1 = ingest_file(IngestRequest(f1, "S1", SourceType.DOCUMENT))
    
    f2 = tmp_path / "doc_copy.txt"
    f2.write_text("content")
    id2 = ingest_file(IngestRequest(f2, "S2", SourceType.DOCUMENT))
    
    mgr = JobManager()
    jid1 = mgr.submit_job(JobSubmission(id1, JobType.TRANSCRIPTION, {"m":"1"}))
    
    # Complete J1
    j1 = db_session.get(JobModel, jid1)
    j1.status = JobStatus.COMPLETED
    j1.meta = {"res": "done"}
    db_session.commit()
    
    # Submit J2 (Should reuse)
    jid2 = mgr.submit_job(JobSubmission(id2, JobType.TRANSCRIPTION, {"m":"1"}))
    j2 = db_session.get(JobModel, jid2)
    
    assert j2.status == JobStatus.COMPLETED
    assert j2.meta["res"] == "done"
