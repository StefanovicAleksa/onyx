import logging
from pathlib import Path
from app.core.common.enums import SourceType

# Cross-Feature Import (Service calls Service)
from app.features.storage.service.api import storage
from app.features.storage.domain.models import IngestRequest

from ..domain.models import ScanRequest, ScanSummary
from ..data.file_walker import LocalFileWalker

logger = logging.getLogger(__name__)

class SourceScanner:
    """
    Service responsible for bulk ingestion of folders.
    """
    
    def __init__(self):
        self.walker = LocalFileWalker()

    def scan_and_ingest(self, request: ScanRequest) -> ScanSummary:
        summary = ScanSummary()
        logger.info(f"Starting scan of: {request.root_path}")
        
        try:
            for file_path in self.walker.walk(request.root_path, request.recursive):
                summary.files_found += 1
                
                try:
                    # 1. Determine Source Name (Relative path helps organization)
                    # e.g. "Case409 - evidence/audio/call.mp3"
                    try:
                        relative_path = file_path.relative_to(request.root_path)
                    except ValueError:
                        relative_path = file_path.name
                        
                    prefix = f"{request.source_name_prefix} - " if request.source_name_prefix else ""
                    source_name = f"{prefix}{relative_path}"
                    
                    # 2. Determine Type
                    source_type = self._determine_source_type(file_path)
                    
                    if source_type == "SKIP":
                        summary.files_ignored += 1
                        continue

                    # 3. Call Storage Service
                    req = IngestRequest(
                        file_path=file_path,
                        source_name=source_name,
                        source_type=source_type
                    )
                    
                    storage.ingest_file(req)
                    summary.files_ingested += 1
                    
                except Exception as e:
                    error_msg = f"Failed to ingest {file_path.name}: {str(e)}"
                    logger.error(error_msg)
                    summary.errors.append(error_msg)
                    
        except Exception as e:
            summary.errors.append(f"Fatal scan error: {str(e)}")
            
        logger.info(f"Scan complete. Ingested: {summary.files_ingested}/{summary.files_found}")
        return summary

    def _determine_source_type(self, path: Path) -> SourceType:
        """
        Maps file extensions to Onyx SourceTypes.
        """
        ext = path.suffix.lower()
        
        VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
        AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac", ".wma"}
        DOC_EXTS = {".pdf", ".txt", ".docx", ".md", ".rtf"}
        IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}

        if ext in VIDEO_EXTS:
            return SourceType.VIDEO_FILE
        if ext in AUDIO_EXTS:
            return SourceType.AUDIO_FILE
        if ext in DOC_EXTS:
            return SourceType.DOCUMENT
        
        # Currently we don't treat images as primary sources for ingestion 
        # unless OCR is requested, but for now we might skip them or map them.
        # Let's skip unknown types to keep the DB clean.
        return "SKIP"