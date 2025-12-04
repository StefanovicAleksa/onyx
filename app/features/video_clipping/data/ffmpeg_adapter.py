import subprocess
import logging
from app.core.config import settings
from ..domain.interfaces import IClipGenerator
from ..domain.models import ClipRequest

logger = logging.getLogger(__name__)

class FFmpegClipAdapter(IClipGenerator):
    """
    Concrete implementation of IClipGenerator.
    Uses 'Re-encoding' strategy for frame-accurate cuts (critical for legal/medical context).
    """
    
    def create_clip(self, request: ClipRequest) -> None:
        if not request.source_video.exists():
            raise FileNotFoundError(f"Source video not found: {request.source_video.path}")

        request.output_video.ensure_parent_dir()

        # Construction of the "Evidence-Grade" Clipping Command
        # 1. -ss (Seek) placed BEFORE -i is fast, but usually Keyframe-snapped.
        # 2. Re-encoding (libx264) ensures that even if we snap to a keyframe, 
        #    we reconstruct the frames accurately from that point.
        cmd = [
            settings.FFMPEG_BINARY,
            "-y",
            "-ss", str(request.time_range.start_seconds),  # Start Time
            "-i", str(request.source_video.path),          # Input
            "-t", str(request.time_range.duration),        # Duration (End - Start)
            "-c:v", "libx264",                             # Re-encode Video (H.264)
            "-c:a", "aac",                                 # Re-encode Audio (AAC)
            "-strict", "experimental",                     # Often needed for AAC
            str(request.output_video.path)
        ]

        logger.info(f"Executing FFmpeg: {' '.join(cmd)}")
        
        try:
            subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=True
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg Execution Failed. STDERR: {e.stderr}")
            raise RuntimeError(f"Video clipping failed: {e.stderr}") from e