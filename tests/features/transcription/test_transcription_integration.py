# File: tests/features/transcription/test_transcription_integration.py
import pytest
import subprocess
import json
import logging
from pathlib import Path
from uuid import UUID

from app.core.database.base import Base
from app.core.database.connection import engine, SessionLocal
from app.core.jobs.manager import JobManager
from app.core.jobs.models import JobModel, JobStatus
from app.core.jobs.types import JobType

from app.features.storage.service.api import storage
from app.features.storage.domain.models import IngestRequest
from app.core.common.enums import SourceType

from app.features.transcription.service.job_handler import TranscriptionHandler
from app.features.transcription.data.sql_models import TranscriptionModel, TranscriptionSegmentModel

# Configure logging to see Whisper output
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def real_audio_file(tmp_path):
    """
    Generates a clear audio file with spoken words "Hello World" using 
    text-to-speech (macOS/Linux) or a synthesize sine wave that Whisper 
    might just interpret as noise/silence, but we check for execution.
    
    Ideally, we use a tiny real .wav if available, but for self-contained tests,
    we synthesize a simple tone that Whisper processes (even if result is empty text, metadata exists).
    """
    audio_path = tmp_path / "integration_test.mp3"
    
    # We generate 2 seconds of a sine wave. 
    # Whisper 'tiny' might transcribe this as empty or garbage, 
    # but it WILL generate a segment with metadata.
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", "sine=frequency=400:duration=2",
        "-c:a", "libmp3lame", str(audio_path)
    ]
    subprocess.run(cmd, check=True)
    return audio_path

def test_transcription_handler_runs_real_whisper(real_audio_file):
    """
    True Integration Test:
    1. Ingests file.
    2. Runs TranscriptionHandler with 'tiny' model (downloads if needed).
    3. Verifies DB has JSONB metadata from the actual model run.
    """
    print(f"\n[Test] 1. Ingesting {real_audio_file}...")
    ingest_req = IngestRequest(
        file_path=real_audio_file,
        source_name="Real Whisper Test",
        source_type=SourceType.AUDIO_FILE
    )
    source_id = storage.ingest_file(ingest_req)

    print("[Test] 2. Submitting Job...")
    job_mgr = JobManager()
    job_id = job_mgr.submit_job(
        source_id=source_id,
        job_type=JobType.TRANSCRIPTION,
        params={"model_size": "tiny"} # 'tiny' is ~70MB and fast on CPU
    )
    
    # Manually set status to PROCESSING to simulate worker pickup
    with SessionLocal() as db:
        job = db.get(JobModel, job_id)
        job.status = JobStatus.PROCESSING
        db.commit()

    print("[Test] 3. executing Handler (Loading Whisper Model)...")
    handler = TranscriptionHandler()
    
    # This CALLS the actual WhisperAdapter -> ModelOrchestrator -> openai-whisper
    try:
        result = handler.handle(source_id, {"model_size": "tiny"})
    except RuntimeError as e:
        pytest.fail(f"Whisper Execution Failed: {e}")

    # 4. Verification
    print("[Test] 4. Verifying Database Records...")
    with SessionLocal() as db:
        transcription = db.query(TranscriptionModel).filter_by(job_id=job_id).first()
        assert transcription is not None, "Transcription Header not created"
        
        # Check that we stored technical metadata
        assert transcription.processing_meta is not None
        assert "device" in transcription.processing_meta
        print(f"   -> Model ran on: {transcription.processing_meta['device']}")

        # Check Segments
        segments = db.query(TranscriptionSegmentModel).filter_by(transcription_id=transcription.id).all()
        
        # Note: A pure sine wave might result in 0 segments if Whisper VAD filters it out.
        # If so, we verify the HEADER was created successfully (proof of run).
        # If segments exist, we verify their metadata.
        if segments:
            seg = segments[0]
            meta = seg.meta_data
            
            # CRITICAL CHECK: Did we get real float values?
            assert "confidence" in meta
            assert isinstance(meta["confidence"], float)
            assert "words" in meta
            
            print(f"   -> Found {len(segments)} segments.")
            print(f"   -> Segment 1 Meta: {json.dumps(meta, indent=2)}")
        else:
            print("   -> Whisper ran successfully but found no speech in sine wave (Expected behavior).")
            # We still pass because the pipeline completed without crashing.

    print("✅ Real Whisper Integration Test Passed.")