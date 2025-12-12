from enum import Enum

class JobType(str, Enum):
    TRANSCRIPTION = "transcription"
    DIARIZATION = "diarization"
    VAD_ANALYSIS = "vad_analysis"
    AUDIO_EXTRACTION = "audio_extraction"
    VIDEO_CLIPPING = "video_clipping"
    INTELLIGENCE = "intelligence"

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"