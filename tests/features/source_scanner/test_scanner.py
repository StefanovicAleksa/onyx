import pytest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import Base
from app.core.db_models import SourceModel, FileModel
from app.core.enums import SourceType, FileType
from app.features.source_scanner.service.manager import SourceScanner
from app.features.source_scanner.domain.models import ScanRequest

# --- CONFIGURATION ---
TEST_ENGINE = create_engine(settings.DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)

# --- FIXTURES ---

@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """
    Reset DB for each test.
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
def complex_folder_structure(tmp_path):
    """
    Creates a nested folder structure with:
    - 2 Valid Files (1 text, 1 audio)
    - 2 Ignored Files (.DS_Store, .tmp)
    """
    root = tmp_path / "legal_dump"
    root.mkdir()
    
    # 1. Valid Text File
    case_folder = root / "case_alpha"
    case_folder.mkdir()
    (case_folder / "notes.txt").write_text("Valid evidence")
    
    # 2. Valid Audio File
    # We just create an empty file, the scanner only checks extension for type
    (root / "interview.mp3").write_bytes(b"FAKE_AUDIO")
    
    # 3. Ignored Files (Junk)
    (root / ".DS_Store").write_bytes(b"junk")
    (case_folder / "temp.tmp").write_text("temporary garbage")
    
    return root

# --- TESTS ---

def test_bulk_scan_integration(complex_folder_structure, db_session):
    """
    Verifies that the scanner:
    1. Finds all valid files recursively.
    2. Ignores junk files.
    3. Persists them to the DB with correct logical names.
    """
    # 1. Arrange
    scanner = SourceScanner()
    request = ScanRequest(
        root_path=complex_folder_structure,
        source_name_prefix="Import Batch 1",
        recursive=True
    )
    
    # 2. Act
    summary = scanner.scan_and_ingest(request)
    
    # 3. Assert - Summary Report
    # We created 4 files total, but only 2 are valid.
    assert summary.files_ingested == 2
    assert len(summary.errors) == 0
    
    # 4. Assert - Database Persistence
    
    # Check for the Text File
    # Expected Name: "Import Batch 1 - case_alpha/notes.txt"
    text_source = db_session.query(SourceModel).filter(
        SourceModel.name.like("%notes.txt")
    ).first()
    
    assert text_source is not None
    assert text_source.name == "Import Batch 1 - case_alpha/notes.txt"
    assert text_source.source_type == SourceType.DOCUMENT
    
    # Check for the Audio File
    audio_source = db_session.query(SourceModel).filter(
        SourceModel.name.like("%interview.mp3")
    ).first()
    
    assert audio_source is not None
    assert audio_source.source_type == SourceType.AUDIO_FILE
    
    # Verify junk was NOT ingested
    junk_check = db_session.query(SourceModel).filter(
        SourceModel.name.like("%.DS_Store")
    ).first()
    assert junk_check is None
    
    print(f"\n✅ Scan verified: Found {summary.files_ingested} valid files, correctly ignored junk.")