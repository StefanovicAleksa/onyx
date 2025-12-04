import logging
import torch
import whisper
from app.core.config import settings
from app.core.shared_types import MediaFile
from ..domain.interfaces import ITranscriber
from ..domain.models import TranscriptionResult, TranscriptionSegment

logger = logging.getLogger(__name__)

class WhisperAdapter(ITranscriber):
    """
    Implementation of ITranscriber using OpenAI's Whisper (Local).
    """
    
    def __init__(self, model_size: str = "large-v3"):
        self.model_size = model_size
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._model = None # Lazy loading

    def _load_model(self):
        """
        Loads the model into memory only when needed.
        """
        if self._model is None:
            logger.info(f"🧠 Loading Whisper model '{self.model_size}' on {self.device}...")
            try:
                self._model = whisper.load_model(self.model_size, device=self.device)
            except Exception as e:
                logger.error(f"Failed to load Whisper model: {e}")
                raise RuntimeError(f"Could not load Whisper model: {e}")

    def transcribe(self, audio_file: MediaFile) -> TranscriptionResult:
        if not audio_file.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_file.path}")

        self._load_model()
        
        logger.info(f"🎙️ Transcribing {audio_file.path.name}...")
        
        try:
            # Run the transcription
            # fp16=False if on CPU to avoid warnings, though Whisper handles this mostly.
            result_raw = self._model.transcribe(
                str(audio_file.path),
                fp16=(self.device == "cuda")
            )
            
            # Map raw Whisper dictionary to Domain Entities
            segments = []
            for seg in result_raw.get("segments", []):
                segments.append(TranscriptionSegment(
                    start_time=float(seg["start"]),
                    end_time=float(seg["end"]),
                    text=seg["text"].strip()
                ))

            logger.info(f"✅ Transcription complete. Found {len(segments)} segments.")

            return TranscriptionResult(
                source_audio=audio_file,
                language=result_raw.get("language", "unknown"),
                full_text=result_raw.get("text", "").strip(),
                segments=segments,
                model_used=self.model_size
            )

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise RuntimeError(f"Transcription failed: {e}") from e