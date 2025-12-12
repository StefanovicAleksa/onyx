from pathlib import Path
from ..domain.models import ClipRequest, MediaFile, TimeRange
from ..data.ffmpeg_adapter import FFmpegClipAdapter

def create_video_clip(source_path: str, start: float, end: float, dest_path: str) -> None:
    """
    Public Service API: Extract a segment from a video file.
    
    Args:
        source_path: Absolute path to the source video.
        start: Start timestamp in seconds.
        end: End timestamp in seconds.
        dest_path: Absolute path where the clip should be saved.
    """
    # 1. Map Primitives to Domain Objects
    # Source must exist
    source = MediaFile(Path(source_path), validate_exists=True)
    
    # Output does not exist yet, so we disable validation
    output = MediaFile(Path(dest_path), validate_exists=False)
    
    time_range = TimeRange(start_seconds=start, end_seconds=end)
    
    # 2. Create the Request Entity
    request = ClipRequest(
        source_video=source,
        output_video=output,
        time_range=time_range
    )
    
    # 3. Instantiate Adapter
    adapter = FFmpegClipAdapter()
    
    # 4. Execute Logic
    adapter.create_clip(request)