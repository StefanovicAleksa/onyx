# File: app/core/common/enums.py

from enum import Enum, unique

@unique
class FileType(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"
    TEXT = "text"
    UNKNOWN = "unknown"

@unique
class SourceType(str, Enum):
    DEPOSITION = "deposition"
    MEDICAL_RECORD = "medical_record"
    COURT_TRANSCRIPT = "court_transcript"
    VIDEO_FILE = "video_file"
    AUDIO_FILE = "audio_file"
    DOCUMENT = "document"