import pytest
import urllib.request
from pathlib import Path
from app.features.transcription.service.api import transcribe_audio
from app.core.config import settings

# Define paths
TEST_DIR = Path(__file__).parent.parent.parent / "temp_artifacts"
TEST_AUDIO = TEST_DIR / "jfk.flac"

# Official sample from OpenAI's repo (Stable GitHub Link)
JFK_URL = "https://raw.githubusercontent.com/openai/whisper/main/tests/jfk.flac"

@pytest.fixture(scope="module", autouse=True)
def setup_teardown():
    """
    Downloads the 'JFK' speech sample if it doesn't exist.
    """
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Download Real Test Data
    if not TEST_AUDIO.exists():
        print(f"\n⬇️ Downloading JFK sample from {JFK_URL}...")
        try:
            # Add a User-Agent to avoid 403 Forbidden errors from GitHub
            opener = urllib.request.build_opener()
            opener.addheaders = [('User-agent', 'Mozilla/5.0')]
            urllib.request.install_opener(opener)
            
            urllib.request.urlretrieve(JFK_URL, TEST_AUDIO)
        except Exception as e:
            pytest.fail(f"Could not download test audio: {e}")

    yield
    
    # Clean up is optional. Commenting out to save download time on re-runs.
    # if TEST_AUDIO.exists(): TEST_AUDIO.unlink()

def test_transcription_accuracy():
    """
    Verifies that:
    1. The system loads the configured model (large-v3).
    2. It accurately transcribes the JFK quote.
    3. It returns valid timestamps.
    """
    assert TEST_AUDIO.exists(), "Test audio file is missing"
    
    print(f"\n🧪 Testing Transcription using model: {settings.WHISPER_MODEL_NAME}")
    
    # EXECUTE
    result = transcribe_audio(str(TEST_AUDIO))
    
    # ASSERTIONS
    
    # 1. Check Model Usage
    assert result.model_used == settings.WHISPER_MODEL_NAME
    
    # 2. Check Content (Case insensitive partial match)
    # Quote: "And so, my fellow Americans: ask not what your country can do for you..."
    expected_phrase = "ask not what your country can do for you"
    
    print(f"📝 Transcribed: {result.full_text[:100]}...")
    
    assert expected_phrase.lower() in result.full_text.lower(), \
        f"Transcription did not contain expected phrase: '{expected_phrase}'"
    
    # 3. Check Timestamps
    assert len(result.segments) > 0
    first_seg = result.segments[0]
    
    # Timestamps must be non-negative and sequential
    assert first_seg.start_time >= 0.0
    assert first_seg.end_time > first_seg.start_time
    
    print(f"✅ Timestamps verified: Segment 1 ({first_seg.start_time:.2f}s - {first_seg.end_time:.2f}s)")