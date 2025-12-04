import subprocess
import logging
from app.core.config import settings
from ..domain.interfaces import IAudioExtractor
from ..domain.models import AudioExtractionJob

logger = logging.getLogger(__name__)

class FFmpegAudioAdapter(IAudioExtractor):
    """
    Concrete implementation of IAudioExtractor using the system FFmpeg binary.
    """
    
    def extract(self, job: AudioExtractionJob) -> None:
        if not job.source_video.exists():
            raise FileNotFoundError(f"Source video not found: {job.source_video.path}")

        # Ensure output directory exists before running command
        job.output_audio.ensure_parent_dir()

        # Construct FFmpeg command
        # -y: Overwrite output file without asking
        # -vn: Disable video recording
        # -acodec libmp3lame: Force MP3 encoding
        # -b:a: Set audio bitrate
        cmd = [
            settings.FFMPEG_BINARY,
            "-y",                           
            "-i", str(job.source_video.path),
            "-vn",                          
            "-acodec", "libmp3lame",        
            "-b:a", f"{job.bitrate_kbps}k", 
            str(job.output_audio.path)
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