# File: tests/features/diarization/test_diarization_integration.py
import pytest
from uuid import uuid4
from app.core.database.base import Base
from app.core.database.connection import engine, SessionLocal
from app.features.storage.data.sql_models import SourceModel, FileModel
from app.features.diarization.service.api import run_diarization
from app.features.diarization.data.sql_models import SourceSpeakerModel
from app.core.common.enums import SourceType, FileType

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_diarization_creates_speakers():
    """
    Integration: Run Diarization -> Verify Speaker Models created in DB.
    """
    # 1. Setup Mock Source
    source_id = uuid4()
    with SessionLocal() as db:
        # Create Dummy Source with REQUIRED fields (hash, type)
        src = SourceModel(
            id=source_id, 
            name="Diarization Test",
            source_type=SourceType.AUDIO_FILE,
            original_file=FileModel(
                file_path="/tmp/fake_audio.wav", 
                file_size_bytes=100,
                file_hash="dummy_hash_for_test", # FIXED
                file_type=FileType.AUDIO         # FIXED
            )
        )
        db.add(src)
        db.commit()

    # 2. Run Service (Mocked Adapter will return speaker_0, speaker_1)
    # We pass a fake path because our Mock Adapter ignores it
    result = run_diarization("/tmp/fake_audio.wav")
    
    assert result.num_speakers > 0
    assert len(result.segments) > 0
    
    # 3. Persist Logic (Simulating what the Pipeline would do)
    with SessionLocal() as db:
        unique_labels = set(s.speaker_label for s in result.segments)
        
        for label in unique_labels:
            spk = SourceSpeakerModel(
                source_id=source_id,
                detected_label=label,
                user_label=f"Unknown {label}"
            )
            db.add(spk)
        db.commit()

        # 4. Verify DB
        rows = db.query(SourceSpeakerModel).filter_by(source_id=source_id).all()
        assert len(rows) == len(unique_labels)
        assert rows[0].detected_label.startswith("speaker_")
        print(f"\n[Success] Created {len(rows)} speakers: {[r.detected_label for r in rows]}")