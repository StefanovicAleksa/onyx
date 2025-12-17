# File: tests/features/vad/test_vad_integration.py
import pytest
from app.features.vad.service.api import run_vad_analysis
from app.features.vad.domain.models import VadEventType

def test_vad_service_returns_segments():
    """
    Integration: Run VAD -> Check Segment Types.
    """
    # Using the mock adapter logic
    segments = run_vad_analysis("/tmp/any_path.wav")
    
    assert len(segments) > 0
    
    has_speech = any(s.event_type == VadEventType.SPEECH for s in segments)
    has_silence = any(s.event_type == VadEventType.SILENCE for s in segments)
    
    assert has_speech
    assert has_silence
    print(f"\n[Success] VAD returned {len(segments)} segments.")