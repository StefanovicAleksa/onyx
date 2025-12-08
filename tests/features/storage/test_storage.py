import pytest
from pathlib import Path
from app.core.database import Base
from app.core.db_models import FileModel, SourceModel
from app.features.storage.service.api import ingest_file
from app.features.storage.domain.models import IngestRequest
from app.core.enums import SourceType
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

def test_physical_deduplication(tmp_path, db_session):
    content = b"duplicate content"
    f1 = tmp_path / "1.txt"
    f1.write_bytes(content)
    f2 = tmp_path / "2.txt"
    f2.write_bytes(content)
    
    id1 = ingest_file(IngestRequest(f1, "S1", SourceType.DOCUMENT))
    id2 = ingest_file(IngestRequest(f2, "S2", SourceType.DOCUMENT))
    
    assert not f2.exists() # Should be deleted
    count = db_session.query(FileModel).count()
    assert count == 1
