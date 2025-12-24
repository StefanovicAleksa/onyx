import pytest
from uuid import uuid4
from app.core.database.base import Base
from app.core.database.connection import engine, SessionLocal
from app.features.storage.data.sql_models import SourceModel, FileModel
from app.features.transcription.data.sql_models import TranscriptionModel, TranscriptionSegmentModel
from app.features.diarization.service.job_handler import DiarizationHandler
from app.features.diarization.data.sql_models import SourceSpeakerModel
from app.core.common.enums import SourceType, FileType


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_diarization_aligns_speakers_to_text():
    """
    Integration:
    1. Create Source & Text Segments (Timestamps 0.0 - 5.0).
    2. Run Diarization (Mock returns 'speaker_0' for 0.0 - 2.0).
    3. Verify Text Segments get updated with speaker_id.
    """
    # 1. Setup Mock Source & Data
    source_id = uuid4()
    with SessionLocal() as db:
        # A. Create File Record First
        file_rec = FileModel(
            file_path="/tmp/fake_audio.wav",
            file_size_bytes=100,
            file_hash="align_test_hash",
            file_type=FileType.AUDIO
        )
        db.add(file_rec)
        db.flush()  # Generates file_rec.id

        # [cite_start]B. Create Source Record linked to File [cite: 172]
        src = SourceModel(
            id=source_id,
            name="Alignment Test",
            source_type=SourceType.AUDIO_FILE,
            file_id=file_rec.id  # Explicit Foreign Key Link
        )
        db.add(src)
        db.commit()  # Commit source logic

        # C. Create Transcription Header
        trans = TranscriptionModel(
            source_id=source_id,
            job_id=uuid4(),  # Dummy Job ID
            model_used="fake",
            full_text="..."
        )
        db.add(trans)
        db.flush()

        # D. Create Segments
        # Segment at 1.0s (Should match speaker_0 in Mock Adapter)
        seg_match = TranscriptionSegmentModel(
            transcription_id=trans.id,
            start_time=1.0,
            end_time=1.5,
            text="I should be assigned to speaker 0"
        )
        # Segment at 100.0s (Should NOT match anyone)
        seg_no_match = TranscriptionSegmentModel(
            transcription_id=trans.id,
            start_time=100.0,
            end_time=101.0,
            text="I am alone in the void"
        )
        db.add(seg_match)
        db.add(seg_no_match)
        db.commit()

    # 2. Run Handler
    # Note: Our Mock Adapter in `nemo_adapter.py` returns:
    # 0.0-2.0s -> speaker_0
    # 2.0-4.5s -> speaker_1
    handler = DiarizationHandler()
    result = handler.handle(source_id, {})

    # 3. Verify
    assert result["segments_aligned"] >= 1

    with SessionLocal() as db:
        # Check Linked Segment
        linked_seg = db.query(TranscriptionSegmentModel).filter(
            TranscriptionSegmentModel.text.contains("assigned")
        ).first()

        assert linked_seg.speaker_id is not None

        # Check the Speaker Label
        speaker = db.get(SourceSpeakerModel, linked_seg.speaker_id)
        assert speaker.detected_label == "speaker_0"

        # Check Unlinked Segment
        unlinked_seg = db.query(TranscriptionSegmentModel).filter(
            TranscriptionSegmentModel.text.contains("void")
        ).first()
        assert unlinked_seg.speaker_id is None

        print(f"\n[Success] Successfully linked '{linked_seg.text}' to {speaker.user_label}")