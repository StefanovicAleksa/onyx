import subprocess
import logging
import shutil
from pathlib import Path
from ..domain.interfaces import IAudioExtractor
from ..domain.models import AudioExtractionJob
from app.core.config import settings

logger = logging.getLogger(__name__)

class FFmpegAudioExtractor(IAudioExtractor):
    """
    Concrete implementation of IAudioExtractor using the FFmpeg CLI binary.
    """

    def __init__(self):
        self.ffmpeg_binary = self._resolve_binary()

    def _resolve_binary(self) -> str:
        """
        Locates the FFmpeg binary.
        Priority:
        1. Explicit path in settings (good for bundled apps).
        2. System PATH (good for dev/Linux).
        """
        # 1. Check explicit config
        if settings.FFMPEG_BINARY_PATH and shutil.which(settings.FFMPEG_BINARY_PATH):
            return settings.FFMPEG_BINARY_PATH
        
        # 2. Check system PATH
        system_ffmpeg = shutil.which("ffmpeg")
        if system_ffmpeg:
            return system_ffmpeg
            
        raise RuntimeError(
            "FFmpeg binary not found. Please install FFmpeg (sudo apt install ffmpeg) or set FFMPEG_BINARY_PATH."
        )

    def extract(self, job: AudioExtractionJob) -> None:
        """
        Executes the FFmpeg command via subprocess.
        """
        # Ensure output directory exists
        job.output_audio_path.parent.mkdir(parents=True, exist_ok=True)

        # Construct the command
        command = [
            self.ffmpeg_binary,
            "-i", str(job.video_file_path.resolve()),  # Input file
            "-vn",                                     # Disable video recording
            *job.quality_flags,                        # Inject quality flags
            str(job.output_audio_path.resolve()),      # Output file
            "-y"                                       # Overwrite output files without asking
        ]

        logger.info(f"Executing FFmpeg: {' '.join(command)}")

        try:
            # Run the command
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                timeout=300 # 5 Minute timeout to prevent zombie processes
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg Execution Failed. STDERR: {e.stderr}")
            raise RuntimeError(f"FFmpeg extraction failed: {e.stderr}") from e
        except subprocess.TimeoutExpired as e:
            logger.error("FFmpeg process timed out.")
            raise RuntimeError("FFmpeg extraction timed out.") from e