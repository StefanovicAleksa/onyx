import logging
from pathlib import Path

from app.core.enums import SourceType
from app.features.storage.service.api import ingest_file
from app.features.storage.domain.models import IngestRequest

from ..domain.models import ScanRequest, ScanSummary
from ..data.file_walker import LocalFileWalker

logger = logging.getLogger(__name__)

class SourceScanner:
    """
    High-level API for Bulk Ingestion.
    """
    
    def __init__(self):
        self.walker = LocalFileWalker()

    def scan_and_ingest(self, request: ScanRequest) -> ScanSummary:
        """
        Walks the folder and triggers ingestion for every valid file found.
        """
        summary = ScanSummary()
        
        logger.info(f"📂 Starting scan of: {request.root_path}")
        
        try:
            # 1. Iterate over valid files
            for file_path in self.walker.walk(request.root_path, request.recursive):
                summary.files_found += 1
                
                try:
                    # 2. Determine logical source name
                    # e.g. Root=/data/legal, File=/data/legal/case_1/doc.pdf
                    # Relative = case_1/doc.pdf
                    # Source Name = "Prefix - case_1/doc.pdf"
                    relative_path = file_path.relative_to(request.root_path)
                    source_name = f"{request.source_name_prefix} - {relative_path}"
                    
                    # 3. Detect rough SourceType (Defaulting to Document for generic scan)
                    # You could add logic here to map extensions to SourceTypes
                    current_type = self._determine_source_type(file_path)

                    # 4. Construct Ingestion Request (Calls Storage Feature)
                    ingest_req = IngestRequest(
                        file_path=file_path,
                        source_name=source_name,
                        source_type=current_type
                    )
                    
                    ingest_file(ingest_req)
                    summary.files_ingested += 1
                    
                except Exception as e:
                    error_msg = f"Failed to ingest {file_path.name}: {str(e)}"
                    logger.error(error_msg)
                    summary.errors.append(error_msg)
                    
        except Exception as e:
            logger.critical(f"Scan failed fatally: {e}")
            summary.errors.append(str(e))
            
        logger.info(f"✅ Scan Complete. Ingested {summary.files_ingested}/{summary.files_found} files.")
        return summary

    def _determine_source_type(self, path: Path) -> SourceType:
        """
        Simple heuristic mapping.
        """
        ext = path.suffix.lower()
        if ext in {".mp4", ".mov", ".avi", ".mkv"}:
            return SourceType.VIDEO_FILE
        if ext in {".mp3", ".wav", ".flac", ".m4a"}:
            return SourceType.AUDIO_FILE
        # Default fallback
        return SourceType.DOCUMENT