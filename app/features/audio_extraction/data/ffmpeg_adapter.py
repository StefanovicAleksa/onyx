import subprocess
import logging
from app.core.config import settings
from ..domain.interfaces import IAudioExtractor
from ..domain.models import AudioExtractionTask

logger = logging.getLogger(__name__)

class FFmpegAudioAdapter(IAudioExtractor):
    """
    Concrete implementation of IAudioExtractor using the system FFmpeg binary.
    """
    
    def extract(self, task: AudioExtractionTask) -> None:
        if not task.source_video.exists():
            raise FileNotFoundError(f"Source video not found: {task.source_video.path}")

        # Ensure output directory exists before running command
        task.output_audio.ensure_parent_dir()

        # Construct FFmpeg command
        cmd = [
            settings.FFMPEG_BINARY,
            "-y",                           
            "-i", str(task.source_video.path),
            "-vn",                          
            "-acodec", "libmp3lame",        
            "-b:a", f"{task.bitrate_kbps}k", 
            str(task.output_audio.path)
        ]

        logger.info(f"Executing FFmpeg: {' '.join(cmd)}")
        
        try:
            # check=True raises CalledProcessError on non-zero exit code
            subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=True
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg Execution Failed. STDERR: {e.stderr}")
            raise RuntimeError(f"Audio extraction failed: {e.stderr}") from e
