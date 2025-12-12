import pytest
from pathlib import Path
from app.core.database.base import Base
from app.core.database.connection import engine, SessionLocal
from app.core.common.enums import SourceType
from app.features.storage.data.sql_models import SourceModel
from app.features.source_scanner.service.scanner import SourceScanner
from app.features.source_scanner.domain.models import ScanRequest

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_scanner_ingests_valid_files(tmp_path):
    """
    Verifies:
    1. Scanner finds valid files.
    2. Scanner skips ignored files (.DS_Store).
    3. Scanner skips unknown extensions (.exe).
    4. Scanner correctly identifies Types (Audio vs Video).
    5. Storage service is actually called (Sources created).
    """
    
    # 1. Setup Directory Structure
    # /data
    #   /video
    #     interview.mp4
    #   /audio
    #     recording.wav
    #   /junk
    #     .DS_Store
    #     virus.exe
    
    video_dir = tmp_path / "video"
    video_dir.mkdir()
    (video_dir / "interview.mp4").write_text("fake video content")
    
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    (audio_dir / "recording.wav").write_text("fake audio content")
    
    junk_dir = tmp_path / "junk"
    junk_dir.mkdir()
    (junk_dir / ".DS_Store").write_text("system junk")
    (junk_dir / "virus.exe").write_text("binary junk")
    
    # 2. Run Scanner
    scanner = SourceScanner()
    request = ScanRequest(
        root_path=tmp_path,
        source_name_prefix="TestBatch",
        recursive=True
    )
    
    summary = scanner.scan_and_ingest(request)
    
    # 3. Verify Summary
    # Found: 4 files total
    # Ingested: 2 (mp4, wav)
    # Ignored: 1 (.exe is skipped by logic, .DS_Store by walker)
    
    # Note: .DS_Store is skipped by the walker, so it doesn't count towards 'files_found' 
    # if the walker implementation filters early. The Walker we wrote filters dirs and files.
    # So files_found should be 3 (interview, recording, virus). Virus returns SKIP type.
    
    assert summary.files_ingested == 2
    assert len(summary.errors) == 0
    
    # 4. Verify Database
    with SessionLocal() as db:
        sources = db.query(SourceModel).all()
        assert len(sources) == 2
        
        # Check Types
        video_src = next(s for s in sources if "interview.mp4" in s.name)
        assert video_src.source_type == SourceType.VIDEO_FILE
        assert "TestBatch" in video_src.name
        
        audio_src = next(s for s in sources if "recording.wav" in s.name)
        assert audio_src.source_type == SourceType.AUDIO_FILE