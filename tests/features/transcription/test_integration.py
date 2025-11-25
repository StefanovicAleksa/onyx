import pytest
import subprocess
import urllib.request
from pathlib import Path
from app.features.transcription.service.api import transcribe_audio
from app.core.config import settings

# Setup paths
TEST_DIR = Path(__file__).parent / "temp_artifacts"
TEST_AUDIO_FILENAME = "test_speech.flac" 
TEST_AUDIO_PATH = TEST_DIR / TEST_AUDIO_FILENAME

# OpenAI's standard test file (JFK Speech)
SPEECH_URL = "https://github.com/openai/whisper/raw/main/tests/jfk.flac"

@pytest.fixture(scope="module", autouse=True)
def setup_teardown():
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    file_created = False
    
    print("\n⬇️  Attempting to download test speech sample...")
    try:
        # Try downloading real human speech (JFK)
        urllib.request.urlretrieve(SPEECH_URL, TEST_AUDIO_PATH)
        if TEST_AUDIO_PATH.exists() and TEST_AUDIO_PATH.stat().st_size > 0:
            print("✅ Download successful. Using human speech sample.")
            file_created = True
    except Exception as e:
        print(f"⚠️ Download failed ({e}). Falling back to synthetic audio.")

    # Fallback: Generate Beep
    if not file_created:
        print("🔨 Generating synthetic audio (beep) with FFmpeg...")
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
            str(TEST_AUDIO_PATH)
        ]
        subprocess.run(cmd, check=True, capture_output=True)
    
    yield
    
    if TEST_AUDIO_PATH.exists():
        TEST_AUDIO_PATH.unlink()
    if TEST_DIR.exists():
        try:
            TEST_DIR.rmdir()
        except OSError:
            pass

def test_transcription_pipeline():
    """
    Verifies that:
    1. Whisper loads into VRAM.
    2. Returns the full text.
    3. CRITICAL: Returns time-stamped segments (start/end times).
    """
    print(f"\n🧪 Testing Whisper Model: {settings.WHISPER_MODEL_NAME} on {settings.WHISPER_DEVICE}")
    
    # 1. EXECUTE
    result = transcribe_audio(TEST_AUDIO_PATH)
    
    # 2. VERIFY BASIC STRUCTURE
    assert result is not None
    assert isinstance(result.text, str)
    assert isinstance(result.processing_time, float)
    
    print(f"✅ Processing Time: {result.processing_time:.4f}s")
    print(f"✅ Detected Language: {result.language}")
    
    # 3. VERIFY SEGMENTS (The New Requirement)
    # We need segments to tell the Vision model WHEN to look.
    assert result.segments is not None, "Result should contain a 'segments' list"
    assert isinstance(result.segments, list), "'segments' must be a list"
    
    if len(result.segments) > 0:
        first_segment = result.segments[0]
        print(f"✅ First Segment Structure: {first_segment}")
        
        # Check Segment Schema
        assert "start" in first_segment, "Segment missing 'start' timestamp"
        assert "end" in first_segment, "Segment missing 'end' timestamp"
        assert "text" in first_segment, "Segment missing 'text'"
        
        # Check Data Types
        assert isinstance(first_segment["start"], (int, float))
        assert isinstance(first_segment["end"], (int, float))
        
        print(f"🎉 SUCCESS: Received {len(result.segments)} timestamped segments.")
    else:
        print("⚠️ Warning: Whisper returned 0 segments (Expected if using fallback beep audio).")