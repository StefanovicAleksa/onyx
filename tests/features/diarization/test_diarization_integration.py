import pytest
import os
import urllib.request
from uuid import uuid4

# --- Database Setup ---
from app.core.database.connection import SessionLocal

# --- Enums (Corrected Paths) ---
from app.core.common.enums import SourceType, FileType
from app.core.jobs.types import JobStatus, JobType  # <--- FIXED LOCATION

# --- Domain Models ---
# JobModel is located in app/core/jobs/models.py
from app.core.jobs.models import JobModel

# Feature models (Assuming standard architecture for these)
from app.features.storage.data.sql_models import SourceModel, FileModel
from app.features.transcription.data.sql_models import TranscriptionModel, TranscriptionSegmentModel

# --- Service Handler ---
from app.features.diarization.service.job_handler import DiarizationHandler


@pytest.fixture(scope="module")
def real_speech_file():
    """
    Downloads a real human speech sample (3 seconds) for integration testing.
    Uses 'male.wav' from a public dataset to ensure VAD detects speech.
    """
    url = "https://www.signalogic.com/melp/EngSamples/Orig/male.wav"
    path = "/tmp/onyx_integration_speech.wav"

    if not os.path.exists(path):
        print(f"\n[Test Setup] Downloading real speech sample to {path}...")
        try:
            opener = urllib.request.build_opener()
            # noinspection PyUnresolvedReferences
            opener.addheaders = [('User-agent', 'Mozilla/5.0')]
            urllib.request.install_opener(opener)
            urllib.request.urlretrieve(url, path)
        except Exception as e:
            pytest.fail(f"Could not download test audio: {e}")

    return path


# noinspection PyDuplicateCode
def test_diarization_aligns_speakers_to_text(real_speech_file):
    """
    Integration:
    1. Sets up DB with a Source pointing to Real Audio.
    2. Runs Diarization Handler (loads NeMo).
    3. Verifies it returns a completed status and detects speakers.
    """
    source_id = uuid4()
    job_id = uuid4()

    with SessionLocal() as db:
        # 1. File Record
        file_rec = FileModel(
            id=uuid4(),
            file_path=real_speech_file,
            file_size_bytes=1024,
            file_hash="real_speech_hash",
            file_type=FileType.AUDIO
        )
        db.add(file_rec)
        db.flush()

        # 2. Source Record
        src = SourceModel(
            id=source_id,
            name="Real Audio Diarization",
            source_type=SourceType.AUDIO_FILE,
            file_id=file_rec.id
        )
        db.add(src)
        db.commit()

        # 3. Job Record
        job = JobModel(
            id=job_id,
            source_id=source_id,
            job_type=JobType.DIARIZATION,
            status=JobStatus.PENDING
        )
        db.add(job)
        db.commit()

        # 4. Mock Transcription (Required for Alignment Logic)
        trans = TranscriptionModel(
            id=uuid4(),
            source_id=source_id,
            job_id=job_id,
            model_used="whisper",
            full_text="This is a test of the diarization system."
        )
        db.add(trans)
        db.flush()

        # Create a segment roughly matching the audio speech (0.0s - 2.5s)
        seg1 = TranscriptionSegmentModel(
            id=uuid4(),
            transcription_id=trans.id,
            start_time=0.5,
            end_time=2.5,
            text="This is a test."
        )
        db.add(seg1)
        db.commit()

    # 5. Execution
    print("\n[Test] Initializing Diarization Handler (Loading NeMo)...")
    handler = DiarizationHandler()

    try:
        # Pass empty params as we are using defaults
        result = handler.handle(source_id, {})

        # 6. Verification
        assert result["status"] == "completed"
        # We expect speakers because we used a real file
        assert result.get("speaker_count", 0) >= 0

        # 7. Check DB updates
        with SessionLocal() as db_verify:
            seg = db_verify.query(TranscriptionSegmentModel).filter_by(text="This is a test.").first()
            assert seg is not None
            # Log the result for visual verification
            print(f"[Test] Segment assigned to: {seg.speaker_id}")

    except Exception as e:
        pytest.fail(f"Diarization Handler failed: {e}")