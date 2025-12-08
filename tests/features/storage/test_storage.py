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
    
    Changed scope from 'module' to 'function' to ensure test isolation.
    """
    # 1. Create Tables
    Base.metadata.create_all(bind=TEST_ENGINE)
    yield
    # 2. Cleanup (Drop Tables)
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
    # Using Session.get() instead of Query.get() for SQLAlchemy 2.0 compliance
    source_record = db_session.get(SourceModel, source_id)
    assert source_record is not None
    assert source_record.name == "Deposition - Witness A"
    assert source_record.source_type == SourceType.DEPOSITION
    
    file_record = source_record.original_file
    assert file_record is not None
    assert file_record.file_type == FileType.TEXT
    # The original file should be deleted (moved)
    assert not original_path.exists() 
    # The new path should exist in artifacts
    assert Path(file_record.file_path).exists()

    # Cleanup: Remove the artifact created by this test
    if Path(file_record.file_path).exists():
        Path(file_record.file_path).unlink()

def test_deduplication_flow(tmp_path, db_session):
    """
    Verifies that ingesting the EXACT same content twice results in:
    - 1 File Record (Deduplicated)
    - 2 Source Records (Logical separation)
    """
    # 1. Create two files with identical content
    file_1 = tmp_path / "copy_1.txt"
    file_1.write_text("Identical Content")
    
    file_2 = tmp_path / "copy_2.txt"
    file_2.write_text("Identical Content")

    # 2. Ingest First Copy
    req1 = IngestRequest(file_path=file_1, source_name="Copy 1", source_type=SourceType.DOCUMENT)
    id1 = ingest_file(req1)

    # 3. Ingest Second Copy
    req2 = IngestRequest(file_path=file_2, source_name="Copy 2", source_type=SourceType.DOCUMENT)
    id2 = ingest_file(req2)

    # 4. Assertions
    assert id1 != id2, "Source IDs must be unique even for same file"

    source1 = db_session.get(SourceModel, id1)
    source2 = db_session.get(SourceModel, id2)

    # Both sources should point to the SAME physical file ID
    assert source1.file_id == source2.file_id
    
    # Verify we only have 1 row in the files table for this hash
    total_files = db_session.query(FileModel).count()
    assert total_files == 1

    # Cleanup artifact
    Path(source1.original_file.file_path).unlink()