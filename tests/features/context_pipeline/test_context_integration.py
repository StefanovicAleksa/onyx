import pytest
from uuid import uuid4, UUID
from sqlalchemy.orm import Session

# We use SessionLocal so we share the same connection factory as the App
from app.core.database.connection import SessionLocal, engine
from app.core.database.base import Base
from app.core.common.enums import SourceType, FileType

# Import Models
from app.core.jobs.models import JobModel, JobStatus
from app.core.jobs.types import JobType
from app.features.storage.data.sql_models import SourceModel, FileModel
from app.features.transcription.data.sql_models import TranscriptionModel, TranscriptionSegmentModel
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
    Creates a Source with a Transcription and 100 Segments.
    
    CRITICAL CHANGE: We use SessionLocal() instead of db_session.
    This ensures we COMMIT the data to the real DB so the Service 
    (which opens its own connection) can actually see it.
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
        db.commit() # Commit early to handle FKs safely

        # 2. Create Job (REQUIRED for Foreign Key Constraint)
        job_id = uuid4()
        job_rec = JobModel(
            id=job_id,
            source_id=source_id,
            job_type=JobType.TRANSCRIPTION,
            status=JobStatus.COMPLETED
        )
        db.add(job_rec)
        db.commit()

        # 3. Create Transcription Header
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

        # 4. Create 100 Segments
        # "word " * 10 is approx 10-12 tokens.
        start_time = 0.0
        for i in range(100):
            seg_text = "word " * 10 
            
            seg = TranscriptionSegmentModel(
                transcription_id=trans_id,
                start_time=start_time,
                end_time=start_time + 1.0,
                text=f"Seg{i}: {seg_text}"
            )
            db.add(seg)
            start_time += 1.0

        db.commit() # FINAL COMMIT - Data is now visible to the Orchestrator
        return source_id
        
    finally:
        db.close()

# --- Tests ---

def test_context_pipeline_sliding_window(seeded_source):
    """
    Verifies that the pipeline correctly chunks segments into windows
    and handles the 90/10/80 split.
    """
    source_id = seeded_source
    
    # 1. Setup Config
    # Limit = 200 tokens.
    params = {
        "context_window_limit": 200, 
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
        windows = db.query(ContextWindowModel)\
                    .filter_by(source_id=source_id)\
                    .order_by(ContextWindowModel.window_index)\
                    .all()
        
        assert len(windows) > 1, "Should have created multiple windows"
        
        # Check Window 0
        w0 = windows[0]
        assert w0.window_index == 0
        
        # Check Provenance Links
        links_w0 = db.query(WindowSegmentLink).filter_by(window_id=w0.id).all()
        assert len(links_w0) > 0
        print(f"[Test] Window 0 has {len(links_w0)} segments.")

        # Check Overlap in Window 1
        w1 = windows[1]
        links_w1 = db.query(WindowSegmentLink).filter_by(window_id=w1.id).all()
        
        ids_0 = {link.transcription_segment_id for link in links_w0}
        ids_1 = {link.transcription_segment_id for link in links_w1}
        
        overlap_ids = ids_0.intersection(ids_1)
        assert len(overlap_ids) > 0, "Window 1 should overlap with Window 0"
        print(f"[Test] Verified Overlap: {len(overlap_ids)} segments shared.")

def test_provenance_reverse_engineering(seeded_source):
    """
    Verifies we can start from a Window and find the exact Video Timestamp.
    """
    source_id = seeded_source
    handler = ContextPipelineHandler()
    handler.handle(source_id, {"context_window_limit": 500})
    
    with SessionLocal() as db:
        # 1. Pick a random window
        window = db.query(ContextWindowModel).filter_by(source_id=source_id).first()
        assert window is not None
        
        # 2. "Reverse Engineer" query
        links = db.query(WindowSegmentLink).filter_by(window_id=window.id).all()
        segment_ids = [l.transcription_segment_id for l in links]
        
        # 3. Verify we can get Time
        segments = db.query(TranscriptionSegmentModel).filter(
            TranscriptionSegmentModel.id.in_(segment_ids)
        ).order_by(TranscriptionSegmentModel.start_time).all()
        
        assert len(segments) > 0
        first_seg = segments[0]
        last_seg = segments[-1]
        
        print(f"\n[Test] Provenance Check:")
        print(f"   Window ID: {window.id}")
        print(f"   Derived Time Range: {first_seg.start_time}s -> {last_seg.end_time}s")
        
        assert first_seg.start_time >= 0.0
        assert last_seg.end_time > first_seg.start_time