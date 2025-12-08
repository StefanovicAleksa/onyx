from enum import Enum, unique

@unique
class FileType(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"
    TEXT = "text"
    CODE = "code"
    UNKNOWN = "unknown"

@unique
class SourceType(str, Enum):
    DEPOSITION = "deposition"
    MEDICAL_RECORD = "medical_record"
    COURT_TRANSCRIPT = "court_transcript"
    VIDEO_FILE = "video_file"
    AUDIO_FILE = "audio_file"
    DOCUMENT = "document"

@unique
class JobType(str, Enum):
    AUDIO_EXTRACTION = "audio_extraction"
    TRANSCRIPTION = "transcription"
    TEXT_EMBEDDING = "text_embedding"
    IMAGE_DESCRIPTION = "image_description"
    INGESTION = "ingestion"

@unique
class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
