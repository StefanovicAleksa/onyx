import pytest
from app.core.database import Base
from app.core.db_models import SourceModel
from app.features.source_scanner.service.manager import SourceScanner
from app.features.source_scanner.domain.models import ScanRequest
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

def test_scanner(tmp_path, db_session):
    (tmp_path / "valid.txt").write_text("ok")
    (tmp_path / ".DS_Store").write_text("junk")
    
    scn = SourceScanner()
    summary = scn.scan_and_ingest(ScanRequest(tmp_path, "Batch"))
    
    assert summary.files_ingested == 1
    assert db_session.query(SourceModel).count() == 1
