from pathlib import Path
from app.core.shared_types import MediaFile
from ..domain.models import AudioExtractionJob
from ..data.ffmpeg_adapter import FFmpegAudioAdapter

def extract_audio_from_video(video_path: str, output_path: str) -> None:
    """
    Public Service API: Extracts audio track from a video file.
    
    Args:
        video_path: Absolute or relative path to the input video.
        output_path: Destination path for the mp3 file.
        
    Raises:
        FileNotFoundError, RuntimeError
    """
    # 1. Map primitive strings to Domain Entities
    source = MediaFile(Path(video_path))
    output = MediaFile(Path(output_path))
    
    # 2. Create the Job
    job = AudioExtractionJob(source_video=source, output_audio=output)
    
    # 3. Instantiate the Adapter (Dependency Injection)
    # In a larger app, a DI container would inject this.
    adapter = FFmpegAudioAdapter()
    
    # 4. Execute Logic
    adapter.extract(job)