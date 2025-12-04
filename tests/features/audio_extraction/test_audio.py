import pytest
import subprocess
from pathlib import Path
from app.features.audio_extraction.service.api import extract_audio_from_video

# Define paths for test artifacts
TEST_DIR = Path(__file__).parent.parent.parent / "temp_artifacts"
TEST_VIDEO = TEST_DIR / "src_audio_test.mp4"
TEST_AUDIO_OUT = TEST_DIR / "output_audio.mp3"

@pytest.fixture(scope="module", autouse=True)
def setup_teardown():
    """
    Creates a synthetic video file using FFmpeg before tests run,
    and cleans up afterwards.
    """
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    
    # Generate a 2-second test video with a sine wave audio track
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=2:size=320x240:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=1000:duration=2",
        "-c:v", "libx264", "-c:a", "aac", 
        str(TEST_VIDEO)
    ]
    
    # We use subprocess directly here to ensure the TEST SETUP is valid 
    # independent of our app code.
    subprocess.run(cmd, check=True, capture_output=True)
    
    yield
    
    # Cleanup
    if TEST_VIDEO.exists(): TEST_VIDEO.unlink()
    if TEST_AUDIO_OUT.exists(): TEST_AUDIO_OUT.unlink()

def test_audio_extraction_flow():
    """
    Integration Test:
    Verifies that extract_audio_from_video produces a valid MP3 file
    from a valid MP4 source.
    """
    assert TEST_VIDEO.exists(), "Test setup failed to create source video"
    
    # EXECUTE SERVICE
    extract_audio_from_video(str(TEST_VIDEO), str(TEST_AUDIO_OUT))
    
    # ASSERT
    assert TEST_AUDIO_OUT.exists()
    assert TEST_AUDIO_OUT.stat().st_size > 0
    print(f"✅ Created audio file: {TEST_AUDIO_OUT}")