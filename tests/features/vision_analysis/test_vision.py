import pytest
import subprocess
from pathlib import Path
from app.features.vision_analysis.service.api import analyze_video_segment
from app.core.config import settings

TEST_DIR = Path(__file__).parent / "temp_artifacts"
TEST_VIDEO = TEST_DIR / "test_vision.mp4"

@pytest.fixture(scope="module", autouse=True)
def setup_teardown():
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    
    # Generate a 5-second video with a moving test pattern
    # This ensures frames are slightly different
    if not TEST_VIDEO.exists():
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "testsrc=duration=5:size=640x480:rate=30",
            str(TEST_VIDEO)
        ]
        subprocess.run(cmd, check=True, capture_output=True)
    
    yield
    
    if TEST_VIDEO.exists():
        TEST_VIDEO.unlink()
    if TEST_DIR.exists():
        try:
            TEST_DIR.rmdir()
        except OSError:
            pass

def test_vision_segment_pipeline():
    """
    Tests the full flow:
    1. Extract frames for range 1.0s - 4.0s (Should get ~3 frames)
    2. Load Qwen2-VL (4-bit)
    3. Describe the video segment
    """
    print(f"\n🧪 Testing Vision Pipeline ({settings.VISION_MODEL_NAME})...")
    
    start_time = 1.0
    end_time = 4.0
    query = "Describe the visual pattern."
    
    # EXECUTE
    # This triggers Model Lifecycle -> Load Qwen -> Analyze -> Unload
    result = analyze_video_segment(TEST_VIDEO, start_time, end_time, query)
    
    # VERIFY
    assert result is not None
    print(f"✅ Vision Description: {result.description}")
    
    # Basic validation
    assert result.timestamp_start == start_time
    assert result.timestamp_end == end_time
    assert len(result.description) > 5