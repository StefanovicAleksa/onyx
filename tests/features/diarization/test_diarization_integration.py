import pytest
import subprocess
from pathlib import Path
from app.core.database.connection import SessionLocal
from app.features.storage.data.sql_models import SourceModel, FileModel
from app.core.common.enums import SourceType, FileType
from app.features.diarization.service.job_handler import DiarizationHandler
from app.features.diarization.data.sql_models import SourceSpeakerModel

@pytest.fixture
def mock_diarization_file(tmp_path):
    """Restored Fixture: Creates a fake audio file."""
    audio_path = tmp_path / "meeting_real.wav"
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", "sine=frequency=400:duration=2",
        str(audio_path)
    ]
    subprocess.run(cmd, check=True)
    return audio_path

def test_diarization_real_pipeline(mock_diarization_file):
    # 1. Setup DB
    with SessionLocal() as db:
        f = FileModel(
            file_path=str(mock_diarization_file),
            file_size_bytes=1000,
            file_hash="dia_real_hash",
            file_type=FileType.AUDIO
        )
        db.add(f)
        db.flush()
        
        s = SourceModel(
            name="Real Diarization Test",
            source_type=SourceType.AUDIO_FILE,
            file_id=f.id
        )
        db.add(s)
        db.commit()
        source_id = s.id

    # 2. Run Handler
    handler = DiarizationHandler()
    result = handler.handle(source_id, {})
    
    # 3. Verify
    assert "speakers_found" in result
    assert "new_profiles_created" in result
    
    # 4. Check DB
    with SessionLocal() as db:
        speakers = db.query(SourceSpeakerModel).filter_by(source_id=source_id).all()
        assert len(speakers) == result["speakers_found"]