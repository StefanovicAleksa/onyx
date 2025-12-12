from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class ExtractionConfig:
    """
    Configuration parameters for audio extraction.
    Defaulting to high-quality MP3 for Whisper accuracy.
    """
    bitrate_kbps: int = 192
    sample_rate_hz: int = 44100
    channels: int = 1  # Mono is often sufficient for speech recognition
    format: str = "mp3"

@dataclass
class ExtractionResult:
    """
    The result of a successful extraction.
    """
    output_path: Path
    format: str
    duration_seconds: float = 0.0

class IAudioExtractor(ABC):
    """
    Contract for extracting audio from video files.
    """
    @abstractmethod
    def extract_audio(self, video_path: Path, output_dir: Path, config: ExtractionConfig) -> ExtractionResult:
        """
        Extracts audio track from the given video file.
        
        Args:
            video_path: Path to the source video.
            output_dir: Directory where the output audio should be saved.
            config: Audio encoding parameters.
            
        Returns:
            ExtractionResult containing the path to the new audio file.
        """
        pass