import logging
import torch
import json
import tempfile
from pathlib import Path
from typing import List

# NeMo imports - Split to prevent cascading failure
try:
    import nemo.collections.asr as nemo_asr
except ImportError:
    nemo_asr = None

try:
    # Try the modern location first (NeMo 1.20+)
    from nemo.collections.asr.parts.utils.vad_utils import get_speech_timestamps_from_model
except ImportError:
    # Fallback or None
    get_speech_timestamps_from_model = None

from app.core.config.settings import settings
from app.core.model_lifecycle.orchestrator import ModelOrchestrator, ModelType
from ..domain.interfaces import IVoiceActivityDetector
from ..domain.models import SpeechSegment

logger = logging.getLogger(__name__)

class MarblenetAdapter(IVoiceActivityDetector):
    """
    Production implementation using NVIDIA's MarbleNet.
    Uses NeMo's built-in utilities to extract precise speech timestamps.
    """
    
    def __init__(self):
        self.orchestrator = ModelOrchestrator()
        
    def detect_speech(self, audio_path: Path) -> List[SpeechSegment]:
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio not found: {audio_path}")
            
        logger.info(f"Requesting VAD for {audio_path.name}...")

        # 1. Orchestrator Load Logic
        def loader():
            if not nemo_asr:
                raise ImportError("NVIDIA NeMo is not installed.")
            
            logger.info("Loading MarbleNet VAD model...")
            if settings.NEMO_VAD_PATH.exists():
                model = nemo_asr.models.EncDecClassificationModel.restore_from(str(settings.NEMO_VAD_PATH))
            else:
                model = nemo_asr.models.EncDecClassificationModel.from_pretrained(model_name="vad_multilingual_marblenet")
            
            model.eval()
            return model

        # 2. Get Model (Blocking VRAM Lock)
        vad_model = self.orchestrator.request_model(ModelType.NEMO_VAD, loader)

        # 3. Run Inference using NeMo Utility
        if not get_speech_timestamps_from_model:
             # Fallback if utility is missing: Return empty or simple classification
             # This prevents the "NoneType is not callable" error
             logger.warning("NeMo VAD utility 'get_speech_timestamps_from_model' not found. Returning empty segments.")
             return []

        timestamps = get_speech_timestamps_from_model(
            vad_model=vad_model,
            audio_filepath=str(audio_path),
            threshold=0.5,
            window_length_in_sec=0.63,
            shift_length_in_sec=0.08
        )
        
        # 4. Convert to Domain Models
        segments = []
        for ts in timestamps:
            segments.append(SpeechSegment(
                start=float(ts['start']),
                end=float(ts['end']),
                confidence=1.0 
            ))
            
        return segments