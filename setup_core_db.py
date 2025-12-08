import os
from pathlib import Path

# Base paths
BASE_DIR = Path("app/core")
BASE_DIR.mkdir(parents=True, exist_ok=True)

# 1. app/core/enums.py
enums_content = """from enum import Enum, unique

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
"""

# 2. app/core/config.py (Updated with DB settings)
config_content = """import os
import shutil
from pathlib import Path

class Config:
    # 1. Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    ARTIFACTS_DIR: Path = DATA_DIR / "artifacts"
    
    # 2. Database (PostgreSQL)
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "password")
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "onyx_db")
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # 3. FFmpeg
    FFMPEG_BINARY: str = os.getenv("FFMPEG_BINARY_PATH", shutil.which("ffmpeg") or "ffmpeg")
    
    # 4. Transcription Settings
    WHISPER_MODEL_NAME: str = os.getenv("WHISPER_MODEL_NAME", "large-v3")
    WHISPER_DEVICE: str = "cuda"

    def ensure_dirs(self):
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

settings = Config()
"""

# 3. app/core/database.py
database_content = """from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL, 
    echo=False, 
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
"""

# 4. app/core/db_models.py
db_models_content = """import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base
from app.core.enums import FileType, SourceType, JobType, JobStatus

class FileModel(Base):
    __tablename__ = "files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_path = Column(String, nullable=False, unique=True)
    file_size_bytes = Column(Integer, nullable=False)
    file_hash = Column(String, nullable=True, index=True)
    file_type = Column(SQLEnum(FileType), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    sources = relationship("SourceModel", back_populates="original_file")

class SourceModel(Base):
    __tablename__ = "sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    source_type = Column(SQLEnum(SourceType), nullable=False)
    
    file_id = Column(UUID(as_uuid=True), ForeignKey("files.id"), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    original_file = relationship("FileModel", back_populates="sources")
    jobs = relationship("JobModel", back_populates="source")

class JobModel(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False)
    job_type = Column(SQLEnum(JobType), nullable=False)
    status = Column(SQLEnum(JobStatus), default=JobStatus.PENDING, nullable=False, index=True)
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    payload = Column(JSON, default=dict) 
    meta = Column(JSON, default=dict)

    source = relationship("SourceModel", back_populates="jobs")
"""

files_to_create = {
    "enums.py": enums_content,
    "config.py": config_content,
    "database.py": database_content,
    "db_models.py": db_models_content,
}

for filename, content in files_to_create.items():
    file_path = BASE_DIR / filename
    print(f"Generating {file_path}...")
    with open(file_path, "w") as f:
        f.write(content)

print("✅ Core Database files generated successfully.")