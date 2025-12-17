# File: app/features/transcription/data/whisper_adapter.py
import whisper
import torch
import logging
from app.core.config.settings import settings
from app.core.model_lifecycle.orchestrator import ModelOrchestrator, ModelType
from ..domain.interfaces import ITranscriber
from ..domain.models import TranscriptionResult, TranscriptionSegment, WordTiming

logger = logging.getLogger(__name__)

class WhisperAdapter(ITranscriber):
    def __init__(self):
        self.orchestrator = ModelOrchestrator()
        self.device = settings.WHISPER_DEVICE

    def transcribe(self, audio_path: str, model_size: str) -> TranscriptionResult:
        logger.info(f"Requesting Whisper ({model_size}) for {audio_path}...")

        def loader():
            logger.debug(f"Loading Whisper {model_size} into VRAM...")
            return whisper.load_model(model_size, device=self.device)

        model = self.orchestrator.request_model(ModelType.WHISPER, loader)
        use_fp16 = (self.device == "cuda")

        # UPDATED: Enable word_timestamps to get the rich metadata
        result_raw = model.transcribe(
            audio_path, 
            fp16=use_fp16, 
            word_timestamps=True
        )

        segments = []
        for seg in result_raw.get('segments', []):
            
            # Extract Word Timings
            words_list = []
            if 'words' in seg:
                for w in seg['words']:
                    words_list.append(WordTiming(
                        word=w['word'].strip(),
                        start=float(w['start']),
                        end=float(w['end']),
                        confidence=float(w['probability'])
                    ))
            
            segments.append(TranscriptionSegment(
                start=float(seg['start']),
                end=float(seg['end']),
                text=seg['text'].strip(),
                confidence=float(seg.get('avg_logprob', 0.0)), # Approximation using logprob
                words=words_list,
                metadata={
                    "compression_ratio": seg.get('compression_ratio'),
                    "no_speech_prob": seg.get('no_speech_prob')
                }
            ))

        return TranscriptionResult(
            source_file=audio_path,
            language=result_raw.get('language', 'unknown'),
            model_used=model_size,
            full_text=result_raw.get('text', '').strip(),
            segments=segments,
            processing_meta={"device": self.device}
        )