import logging
import time
import torch
import whisper
from pathlib import Path
from ..domain.interfaces import ITranscriber
from ..domain.models import TranscriptionJob, TranscriptionResult
from app.core.config import settings

logger = logging.getLogger(__name__)

class WhisperTranscriber(ITranscriber):
    def __init__(self):
        self.device = settings.WHISPER_DEVICE
        self.model_name = settings.WHISPER_MODEL_NAME
        self.model = self._load_model()

    def _load_model(self):
        logger.info(f"Loading Whisper model '{self.model_name}' on {self.device}...")
        if self.device == "cuda" and not torch.cuda.is_available():
            self.device = "cpu"
        try:
            model = whisper.load_model(self.model_name, device=self.device)
            return model
        except Exception as e:
            raise RuntimeError(f"Could not load Whisper model: {e}") from e

    def transcribe(self, job: TranscriptionJob) -> TranscriptionResult:
        if not job.audio_file_path.exists():
            raise FileNotFoundError(f"Audio file not found: {job.audio_file_path}")

        logger.info(f"🎙️ Transcribing {job.audio_file_path.name}...")
        start_time = time.time()

        try:
            # We run the transcription
            result = self.model.transcribe(
                str(job.audio_file_path.resolve()),
                fp16=(self.device == "cuda")
            )
            
            duration = time.time() - start_time
            logger.info(f"✨ Transcription complete. Time: {duration:.2f}s")

            # Capture the 'segments' list which contains {start, end, text}
            return TranscriptionResult(
                text=result["text"].strip(),
                language=result["language"],
                processing_time=duration,
                segments=result.get("segments", []) 
            )
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise RuntimeError(f"Transcription failed: {e}") from e