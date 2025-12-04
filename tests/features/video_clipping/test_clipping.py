import pytest
import subprocess
from pathlib import Path
from app.features.video_clipping.service.api import create_video_clip

# Define paths for test artifacts
TEST_DIR = Path(__file__).parent.parent.parent / "temp_artifacts"
TEST_VIDEO = TEST_DIR / "src_clip_test.mp4"
TEST_CLIP_OUT = TEST_DIR / "output_clip.mp4"

@pytest.fixture(scope="module", autouse=True)
def setup_teardown():
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create 5-second video with visual counter
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=5:size=320x240:rate=30",
        "-c:v", "libx264", 
        str(TEST_VIDEO)
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    
    yield
    
    if TEST_VIDEO.exists(): TEST_VIDEO.unlink()
    if TEST_CLIP_OUT.exists(): TEST_CLIP_OUT.unlink()

def test_video_clipping_flow():
    """
    Integration Test:
    Verifies that create_video_clip cuts a 1-second segment from a 5-second video.
    """
    assert TEST_VIDEO.exists()
    
    start = 1.0
    end = 2.0
    expected_duration = end - start
    
    # EXECUTE SERVICE
    create_video_clip(str(TEST_VIDEO), start, end, str(TEST_CLIP_OUT))
    
    # ASSERT EXISTENCE
    assert TEST_CLIP_OUT.exists()
    
    # ASSERT DURATION (Using ffprobe to verify the file internals)
    probe_cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration", 
        "-of", "default=noprint_wrappers=1:nokey=1", str(TEST_CLIP_OUT)
    ]
    result = subprocess.run(probe_cmd, capture_output=True, text=True)
    actual_duration = float(result.stdout.strip())
    
    # Allow 0.1s margin of error for codec overhead
    print(f"✅ Clip Duration: {actual_duration}s (Expected ~{expected_duration}s)")
    assert (expected_duration - 0.1) <= actual_duration <= (expected_duration + 0.1)