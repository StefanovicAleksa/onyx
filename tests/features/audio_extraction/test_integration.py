import pytest
import subprocess
from pathlib import Path
from app.features.audio_extraction.service.api import extract_audio
from app.core.config import settings

# Define paths for temporary test artifacts
# These will now be created inside 'tests/features/audio_extraction/temp_artifacts'
TEST_DIR = Path(__file__).parent / "temp_artifacts"
TEST_VIDEO = TEST_DIR / "test_src_video.mp4"
TEST_AUDIO_OUTPUT = TEST_DIR / "test_src_video.mp3"

@pytest.fixture(scope="module", autouse=True)
def setup_teardown():
    """
    Test Fixture:
    1. Creates a temporary directory.
    2. Uses FFmpeg to generate a synthetic 1-second video file.
    3. Yields control to the tests.
    4. Cleans up files after tests finish.
    """
    # --- SETUP ---
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    
    # Generate a 1-second test video with audio using FFmpeg lavfi
    cmd = [
        "ffmpeg",
        "-y", # Overwrite
        "-f", "lavfi", "-i", "testsrc=duration=1:size=640x480:rate=30", # Video source
        "-f", "lavfi", "-i", "sine=frequency=1000:duration=1",           # Audio source (beep)
        "-c:v", "libx264", # Video Codec
        "-c:a", "aac",     # Audio Codec (Input)
        str(TEST_VIDEO)
    ]
    
    # Run the generator
    subprocess.run(cmd, check=True, capture_output=True)
    
    yield # Run the tests
    
    # --- TEARDOWN ---
    if TEST_VIDEO.exists():
        TEST_VIDEO.unlink()
    if TEST_AUDIO_OUTPUT.exists():
        TEST_AUDIO_OUTPUT.unlink()
    if TEST_DIR.exists():
        try:
            TEST_DIR.rmdir()
        except OSError:
            pass 

def test_audio_extraction_end_to_end():
    """
    Integration Test:
    Calls the public Service API to extract audio from the generated video.
    """
    assert TEST_VIDEO.exists(), "Test setup failed to create video file."

    # 1. EXECUTE
    result_path = extract_audio(video_path=TEST_VIDEO)

    # 2. VERIFY
    assert result_path == TEST_AUDIO_OUTPUT
    assert result_path.exists()
    assert result_path.stat().st_size > 0
    print(f"Verified audio file created at: {result_path}")

def test_audio_extraction_custom_path():
    """
    Test verifying we can save to a specific custom location.
    """
    custom_output = TEST_DIR / "custom_output.mp3"
    
    try:
        extract_audio(video_path=TEST_VIDEO, output_path=custom_output)
        assert custom_output.exists()
        assert custom_output.stat().st_size > 0
    finally:
        if custom_output.exists():
            custom_output.unlink()