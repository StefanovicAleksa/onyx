# File: app/features/vad/data/marblenet_adapter.py
import logging
from typing import List
from app.core.config.settings import settings
from app.core.model_lifecycle.orchestrator import ModelOrchestrator, ModelType
from ..domain.models import VadSegment, VadEventType

logger = logging.getLogger(__name__)

class MarbleNetAdapter:
    """
    Wrapper for NVIDIA MarbleNet (VAD).
    """
    def __init__(self):
        self.orchestrator = ModelOrchestrator()
    
    def detect_voice(self, audio_path: str) -> List[VadSegment]:
        logger.info(f"Running VAD (MarbleNet) on {audio_path}...")

        def loader():
            # from nemo.collections.asr.models import EncDecClassificationModel
            # return EncDecClassificationModel.from_pretrained(model_name="vad_marblenet")
            
            # Mock for architecture
            class MockVad:
                def process(self, path):
                    # Simulate: 0-5s Speech, 5-10s Silence
                    return [
                        (0.0, 5.0, "speech"),
                        (5.0, 10.0, "silence")
                    ]
            return MockVad()

        # FIXED: Use ModelType.NEMO_VAD instead of MARBLENET_VAD
        model = self.orchestrator.request_model(ModelType.NEMO_VAD, loader)
        
        results = model.process(audio_path)
        
        segments = []
        for start, end, label in results:
            e_type = VadEventType.SPEECH if label == "speech" else VadEventType.SILENCE
            segments.append(VadSegment(
                start=start, 
                end=end, 
                event_type=e_type,
                confidence=0.95
            ))
            
        return segments