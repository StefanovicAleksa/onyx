import subprocess
import logging
from pathlib import Path
from app.core.config.settings import settings
from ..domain.interfaces import IClipGenerator
from ..domain.models import ClipRequest

logger = logging.getLogger(__name__)

class FFmpegClipAdapter(IClipGenerator):
    """
    Concrete implementation of IClipGenerator using FFmpeg.
    Ensures precise cuts by re-encoding streams.
    """
    
    def create_clip(self, request: ClipRequest) -> None:
        # 1. Ensure the directory for the output file exists
        request.output_video.ensure_parent_dir()
        
        # 2. Construct the FFmpeg Command
        # -y: Overwrite output files without asking
        # -ss: Start time (seeking)
        # -i: Input file
        # -t: Duration of the clip
        # -c:v libx264: Re-encode video to ensure frame accuracy (prevents black frames at start)
        # -c:a aac: Re-encode audio
        # -strict experimental: Often required for AAC in older FFmpeg versions
        
        cmd = [
            settings.FFMPEG_BINARY,
            "-y",
            "-ss", str(request.time_range.start_seconds),
            "-i", str(request.source_video.path),
            "-t", str(request.time_range.duration),
            "-c:v", "libx264",
            "-c:a", "aac",
            "-strict", "experimental",
            str(request.output_video.path)
        ]

        logger.info(f"Executing FFmpeg Clip: {' '.join(cmd)}")
        
        try:
            # 3. Execute
            # capture_output=True allows us to log stderr if it fails
            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )
        except subprocess.CalledProcessError as e:
            error_message = e.stderr if e.stderr else "Unknown FFmpeg error"
            logger.error(f"FFmpeg Clipping Failed. STDERR: {error_message}")
            raise RuntimeError(f"Video clipping failed: {error_message}") from e