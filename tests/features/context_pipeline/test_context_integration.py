import pytest
from uuid import uuid4
from app.core.database.connection import SessionLocal, engine
from app.core.database.base import Base
from app.core.common.enums import SourceType, FileType

# Import Models
from app.core.jobs.models import JobModel, JobStatus
from app.core.jobs.types import JobType
from app.features.storage.data.sql_models import SourceModel, FileModel
from app.features.transcription.data.sql_models import TranscriptionModel, TranscriptionSegmentModel
from app.features.diarization.data.sql_models import SourceSpeakerModel
from app.features.context_pipeline.data.sql_models import ContextWindowModel, WindowSegmentLink
from app.features.context_pipeline.service.job_handler import ContextPipelineHandler


# --- Fixtures ---

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    """Ensure tables exist."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def seeded_source():
    """
    Creates a Source with:
    1. A Speaker ("Dr. Test")
    2. A Transcription
    3. 100 Segments linked to "Dr. Test"
    """
    db = SessionLocal()
    try:
        # 1. Create Source & File
        source_id = uuid4()
        file_id = uuid4()

        file_rec = FileModel(
            id=file_id,
            file_path="/tmp/fake_context.txt",
            file_size_bytes=1000,
            file_hash=f"hash_{source_id}",
            file_type=FileType.TEXT
        )
        db.add(file_rec)

        source_rec = SourceModel(
            id=source_id,
            name="Context Pipeline Test Source",
            source_type=SourceType.DOCUMENT,
            file_id=file_id
        )
        db.add(source_rec)
        db.commit()

        # 2. Create Speaker Profile
        speaker_id = uuid4()
        speaker = SourceSpeakerModel(
            id=speaker_id,
            source_id=source_id,
            detected_label="speaker_0",
            user_label="Dr. Test"
        )
        db.add(speaker)
        db.commit()

        # 3. Create Job (REQUIRED for Foreign Key Constraint)
        job_id = uuid4()
        job_rec = JobModel(
            id=job_id,
            source_id=source_id,
            job_type=JobType.TRANSCRIPTION,
            status=JobStatus.COMPLETED
        )
        db.add(job_rec)
        db.commit()

        # 4. Create Transcription Header
        trans_id = uuid4()
        trans_rec = TranscriptionModel(
            id=trans_id,
            source_id=source_id,
            job_id=job_id,
            model_used="fake_whisper",
            full_text="..."
        )
        db.add(trans_rec)
        db.commit()

        # 5. Create 100 Segments linked to Speaker
        start_time = 0.0
        for i in range(100):
            seg_text = "word " * 10

            seg = TranscriptionSegmentModel(
                transcription_id=trans_id,
                start_time=start_time,
                end_time=start_time + 1.0,
                text=f"Seg{i} content",
                speaker_id=speaker_id  # <--- LINKED HERE
            )
            db.add(seg)
            start_time += 1.0

        db.commit()
        return source_id

    finally:
        db.close()


# --- Tests ---

def test_context_pipeline_sliding_window(seeded_source):
    """
    Verifies that the pipeline correctly chunks segments into windows
    and handles the formatting (Timestamps + Speaker Names).
    """
    source_id = seeded_source

    # 1. Setup Config
    # Limit = 250 tokens (Enough to fit a few formatted segments)
    params = {
        "context_window_limit": 250,
        "safe_buffer_ratio": 0.90,
        "overlap_ratio": 0.10
    }

    # 2. Run Pipeline
    handler = ContextPipelineHandler()
    result = handler.handle(source_id, params)

    # 3. Verify Handler Output
    assert result["windows_created"] > 0
    print(f"\n[Test] Created {result['windows_created']} windows.")

    # 4. Verify Database Integrity
    with SessionLocal() as db:
        windows = db.query(ContextWindowModel) \
            .filter_by(source_id=source_id) \
            .order_by(ContextWindowModel.window_index) \
            .all()

        assert len(windows) > 1, "Should have created multiple windows"

        # Check Window 0 Content Format
        w0 = windows[0]
        print(f"\n[Test] Window 0 Sample:\n---\n{w0.text_content[:200]}\n---")

        # KEY ASSERTION: Does it look like a script?
        # Expecting: "[00:00:00] Dr. Test: Seg0 content"
        assert "[00:00:00]" in w0.text_content
        assert "Dr. Test:" in w0.text_content

        # Check Provenance Links
        links_w0 = db.query(WindowSegmentLink).filter_by(window_id=w0.id).all()
        assert len(links_w0) > 0


def test_provenance_reverse_engineering(seeded_source):
    """
    Verifies we can start from a Window and find the exact Video Timestamp.
    """
    source_id = seeded_source

    # Run with larger limit to get fewer windows
    handler = ContextPipelineHandler()
    handler.handle(source_id, {"context_window_limit": 1000})

    with SessionLocal() as db:
        window = db.query(ContextWindowModel).filter_by(source_id=source_id).first()
        assert window is not None

        links = db.query(WindowSegmentLink).filter_by(window_id=window.id).all()
        segment_ids = [l.transcription_segment_id for l in links]

        segments = db.query(TranscriptionSegmentModel).filter(
            TranscriptionSegmentModel.id.in_(segment_ids)
        ).order_by(TranscriptionSegmentModel.start_time).all()

        assert len(segments) > 0
        first_seg = segments[0]

        print(f"\n[Test] Provenance Check:")
        print(f"   Window ID: {window.id}")
        print(f"   Derived Start: {first_seg.start_time}s")

        assert first_seg.start_time >= 0.0