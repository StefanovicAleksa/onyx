import whisper
import torch
import logging
from app.core.config.settings import settings
from app.core.model_lifecycle.orchestrator import ModelOrchestrator, ModelType
from ..domain.interfaces import ITranscriber
from ..domain.models import TranscriptionResult, TranscriptionSegment

logger = logging.getLogger(__name__)

class WhisperAdapter(ITranscriber):
    """
    Concrete implementation using OpenAI's Whisper model.
    Uses ModelOrchestrator to ensure safe VRAM usage.
    """
    def __init__(self):
        self.orchestrator = ModelOrchestrator()
        self.device = settings.WHISPER_DEVICE

    def transcribe(self, audio_path: str, model_size: str) -> TranscriptionResult:
        logger.info(f"Requesting Whisper ({model_size}) for {audio_path}...")

        # 1. Define the Loader Function
        # This only runs if the Orchestrator grants the lock.
        def loader():
            logger.debug(f"Loading Whisper {model_size} into VRAM...")
            return whisper.load_model(model_size, device=self.device)

        # 2. Request Model Access (Blocking)
        model = self.orchestrator.request_model(ModelType.WHISPER, loader)

        # 3. Perform Inference
        # fp16=False prevents errors on some CPUs; True is faster on GPU.
        use_fp16 = (self.device == "cuda")
        result_raw = model.transcribe(audio_path, fp16=use_fp16)

        # 4. Map Raw Output to Domain Models
        segments = []
        for seg in result_raw.get('segments', []):
            segments.append(TranscriptionSegment(
                start=float(seg['start']),
                end=float(seg['end']),
                text=seg['text'].strip(),
                confidence=float(seg.get('avg_logprob', 0.0)) # Simplified confidence
            ))

        return TranscriptionResult(
            source_file=audio_path,
            language=result_raw.get('language', 'unknown'),
            model_used=model_size,
            full_text=result_raw.get('text', '').strip(),
            segments=segments
        )