import pytest
import shutil
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import Base
from app.core.db_models import FileModel, SourceModel
from app.core.enums import SourceType, FileType
from app.features.storage.service.api import ingest_file
from app.features.storage.domain.models import IngestRequest

# --- CONFIGURATION ---
TEST_ENGINE = create_engine(settings.DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)

# --- FIXTURES ---

@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """
    Creates the tables (schema) in Postgres before EACH test start,
    and drops them after EACH test finishes.
    """
    Base.metadata.create_all(bind=TEST_ENGINE)
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)

@pytest.fixture
def db_session():
    """
    Provides a transactional scope around each test.
    """
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def temp_file(tmp_path):
    """
    Creates a dummy file to simulate a user upload.
    """
    p = tmp_path / "test_deposition.txt"
    p.write_text("This is the content of the deposition.")
    return p

# --- TESTS ---

def test_ingest_file_flow(temp_file, db_session):
    """
    Verifies that a new file is correctly hashed, moved, and saved to DB.
    """
    # 1. Arrange
    original_path = temp_file
    assert original_path.exists()
    
    req = IngestRequest(
        file_path=original_path,
        source_name="Deposition - Witness A",
        source_type=SourceType.DEPOSITION
    )

    # 2. Act
    source_id = ingest_file(req)

    # 3. Assert - Check Return Value
    assert source_id is not None

    # 4. Assert - Check Database
    source_record = db_session.get(SourceModel, source_id)
    assert source_record is not None
    assert source_record.name == "Deposition - Witness A"
    
    file_record = source_record.original_file
    assert file_record is not None
    assert file_record.file_type == FileType.TEXT
    
    # 5. Assert - Physical File Movement
    # The original temp file should be GONE (moved)
    assert not original_path.exists() 
    # The new path should EXIST in artifacts
    assert Path(file_record.file_path).exists()

    # Cleanup artifact
    if Path(file_record.file_path).exists():
        Path(file_record.file_path).unlink()

def test_physical_deduplication_and_cleanup(tmp_path, db_session):
    """
    Verifies the Optimization Logic:
    If a duplicate file is uploaded, the system should:
    1. Detect it via hash.
    2. DELETE the new temp file (request.file_path.unlink()).
    3. Reuse the existing File ID and Path.
    """
    # 1. Setup: Create two identical files in temp dir
    content = b"Unique content for this test run"
    
    file_1 = tmp_path / "upload_1.txt"
    file_1.write_bytes(content)
    
    file_2 = tmp_path / "upload_2.txt"
    file_2.write_bytes(content) # Identical content
    
    # 2. Ingest First File (The "Original")
    req1 = IngestRequest(file_path=file_1, source_name="Source 1", source_type=SourceType.DOCUMENT)
    id1 = ingest_file(req1)
    
    # Get the path where the first file ended up
    source1 = db_session.get(SourceModel, id1)
    original_artifact_path = Path(source1.original_file.file_path)
    assert original_artifact_path.exists()
    
    # 3. Ingest Second File (The "Duplicate")
    req2 = IngestRequest(file_path=file_2, source_name="Source 2", source_type=SourceType.DOCUMENT)
    id2 = ingest_file(req2)
    
    # 4. Critical Assertions for Optimization
    
    # A. The second temp file should be DELETED by the system (unlink check)
    assert not file_2.exists(), "The duplicate temp file should have been deleted to save space."
    
    # B. Source 2 should point to Source 1's physical file
    source2 = db_session.get(SourceModel, id2)
    assert source2.original_file.file_path == str(original_artifact_path)
    
    # C. Database should only have 1 File Record
    count = db_session.query(FileModel).count()
    assert count == 1
    
    print(f"\n✅ Deduplication Verified: Temp file deleted, Path reused: {original_artifact_path}")

    # Cleanup
    if original_artifact_path.exists():
        original_artifact_path.unlink()