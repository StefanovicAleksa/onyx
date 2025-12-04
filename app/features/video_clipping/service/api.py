from pathlib import Path
from app.core.shared_types import MediaFile, TimeRange
from ..domain.models import ClipRequest
from ..data.ffmpeg_adapter import FFmpegClipAdapter

def create_video_clip(video_path: str, start: float, end: float, output_path: str) -> None:
    """
    Public Service API: Cuts a segment from a video file.
    
    Args:
        video_path: Path to source video.
        start: Start time in seconds (float).
        end: End time in seconds (float).
        output_path: Destination path for the clip.
    """
    # 1. Map primitives to Domain Entities
    source = MediaFile(Path(video_path))
    output = MediaFile(Path(output_path))
    
    # This TimeRange constructor will raise ValueError if start >= end
    time_range = TimeRange(start_seconds=start, end_seconds=end)
    
    # 2. Create the Request
    request = ClipRequest(source_video=source, output_video=output, time_range=time_range)
    
    # 3. Instantiate Dependency
    adapter = FFmpegClipAdapter()
    
    # 4. Execute Logic
    adapter.create_clip(request)