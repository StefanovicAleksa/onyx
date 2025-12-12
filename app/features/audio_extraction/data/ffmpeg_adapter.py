import subprocess
import logging
from pathlib import Path
from app.core.config.settings import settings
from ..domain.interfaces import IAudioExtractor
from ..domain.models import ExtractionConfig, ExtractionResult

logger = logging.getLogger(__name__)

class FFmpegAdapter(IAudioExtractor):
    def extract_audio(self, video_path: Path, output_dir: Path, config: ExtractionConfig) -> ExtractionResult:
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Output filename: video_name.mp3
        output_filename = f"{video_path.stem}.{config.format}"
        output_path = output_dir / output_filename
        
        # FFmpeg command
        # -vn: Disable video
        # -y: Overwrite output
        # -q:a 0: Best variable bitrate quality for mp3
        cmd = [
            settings.FFMPEG_BINARY,
            "-y",
            "-i", str(video_path),
            "-vn",
            "-acodec", "libmp3lame",
            "-q:a", "2",  # High quality VBR (~190kbps)
            str(output_path)
        ]
        
        logger.info(f"Extracting audio: {' '.join(cmd)}")
        
        try:
            subprocess.run(
                cmd, 
                check=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            logger.error(f"FFmpeg failed: {error_msg}")
            raise RuntimeError(f"Audio extraction failed: {error_msg}")

        return ExtractionResult(
            output_path=output_path,
            format=config.format,
            duration_seconds=0.0 # Could use ffprobe to get exact duration if needed
        )