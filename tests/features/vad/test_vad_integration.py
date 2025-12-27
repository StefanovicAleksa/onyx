import pytest
import os
import urllib.request
from app.features.vad.service.api import run_vad_analysis
from app.features.vad.domain.models import VadEventType


@pytest.fixture(scope="module")
def real_speech_file():
    """
    Downloads a real human speech sample (3 seconds) for integration testing.
    This ensures VAD actually detects speech segments.
    """
    url = "https://www.signalogic.com/melp/EngSamples/Orig/male.wav"
    path = "/tmp/onyx_integration_speech.wav"

    if not os.path.exists(path):
        print(f"\n[Test Setup] Downloading real speech sample to {path}...")
        try:
            opener = urllib.request.build_opener()
            opener.addheaders = [('User-agent', 'Mozilla/5.0')]
            urllib.request.install_opener(opener)
            urllib.request.urlretrieve(url, path)
        except Exception as e:
            pytest.fail(f"Could not download test audio: {e}")

    return path


def test_vad_service_returns_segments(real_speech_file):
    """
    Integration: Run VAD on Real Audio -> Expect Speech Segments.
    """
    print(f"\n[Test] Running VAD on: {real_speech_file}")

    try:
        # 1. Execute Service
        segments = run_vad_analysis(real_speech_file)

        # 2. Basic Structure Validation
        assert isinstance(segments, list)
        assert len(segments) > 0

        # 3. Semantic Validation
        # Since we downloaded a valid speech file, MarbleNet MUST find speech.
        speech_segments = [s for s in segments if s.event_type == VadEventType.SPEECH]
        print(f"[Test] Found {len(speech_segments)} speech segments.")

        # If this fails, the model loaded but inference output was pure silence
        # (unlikely with this specific wav file)
        assert len(speech_segments) > 0

        first = speech_segments[0]
        assert first.start >= 0.0
        assert first.end > first.start

    except Exception as e:
        pytest.fail(f"VAD Pipeline crashed: {e}")