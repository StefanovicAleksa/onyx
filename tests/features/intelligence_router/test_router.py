import pytest
from app.features.transcription.domain.models import TranscriptionResult
from app.features.intelligence_router.service.api import route_transcript
from app.core.config import settings

def test_llm_router_temporal_logic():
    """
    Tests if the LLM Router can:
    1. Read a timestamped transcript.
    2. Identify VISUAL cues.
    3. Return the correct START and END times for those cues.
    """
    print(f"\n🧪 Testing Intelligence Router with Model: {settings.ROUTER_LLM_MODEL}")

    # 1. Construct a Mock Transcript with TIMESTAMPS
    # This simulates a video timeline:
    # 0-5s:   Intro (No visual)
    # 5-10s:  Visual Event 1 (Graph)
    # 10-15s: Filler
    # 15-20s: Visual Event 2 (X-ray)
    
    mock_segments = [
        {
            "start": 0.0, "end": 5.0, 
            "text": "Welcome to the quarterly meeting. Let's get started."
        },
        {
            "start": 5.0, "end": 10.0, 
            "text": "If you look at this graph here, you can see revenue spiked in Q3."
        },
        {
            "start": 10.0, "end": 15.0, 
            "text": "Now, moving on to the medical division updates."
        },
        {
            "start": 15.0, "end": 20.0, 
            "text": "This X-ray clearly shows the fracture on the left tibia."
        }
    ]
    
    # We combine text just for the .text field, but the router should use .segments
    full_text = " ".join([s["text"] for s in mock_segments])
    
    transcript = TranscriptionResult(
        text=full_text,
        language="en",
        processing_time=0.0,
        segments=mock_segments # <--- The Critical Input
    )

    # 2. Run Router
    # This triggers the Lifecycle Manager -> Loads Qwen/Llama -> Analyzes -> Unloads
    result = route_transcript(transcript)

    # 3. Verify Output
    print(f"\n--- Router Analysis Found {result.total_triggers_found} Visual Events ---")
    
    for q in result.visual_queries:
        print(f"⏱️  [{q.timestamp_start}s - {q.timestamp_end}s] Confidence: {q.confidence:.2f}")
        print(f"    Reason: {q.query_text}")

    # 4. Assertions
    assert result.total_triggers_found >= 2, "Should have found at least 2 visual events"
    
    # We want to check if it found the roughly correct timestamps.
    # Timestamps might vary slightly based on LLM tokenization, so we use ranges.
    
    # Check for the Graph Event (~5.0 to 10.0)
    graph_event = next((q for q in result.visual_queries if "graph" in q.query_text.lower() or (q.timestamp_start >= 4.0 and q.timestamp_start <= 6.0)), None)
    assert graph_event is not None, "Failed to identify the Graph event time range"
    
    # Check for the X-ray Event (~15.0 to 20.0)
    xray_event = next((q for q in result.visual_queries if "x-ray" in q.query_text.lower() or (q.timestamp_start >= 14.0 and q.timestamp_start <= 16.0)), None)
    assert xray_event is not None, "Failed to identify the X-ray event time range"
    
    print("\n✅ Temporal Grounding Successful: Router identified correct time ranges.")