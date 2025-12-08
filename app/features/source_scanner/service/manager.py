import logging
from pathlib import Path
from app.core.enums import SourceType
from app.features.storage.service.api import ingest_file
from app.features.storage.domain.models import IngestRequest
from ..domain.models import ScanRequest, ScanSummary
from ..data.file_walker import LocalFileWalker

logger = logging.getLogger(__name__)

class SourceScanner:
    def __init__(self):
        self.walker = LocalFileWalker()

    def scan_and_ingest(self, request: ScanRequest) -> ScanSummary:
        summary = ScanSummary()
        logger.info(f"📂 Starting scan of: {request.root_path}")
        try:
            for file_path in self.walker.walk(request.root_path, request.recursive):
                summary.files_found += 1
                try:
                    relative_path = file_path.relative_to(request.root_path)
                    source_name = f"{request.source_name_prefix} - {relative_path}"
                    current_type = self._determine_source_type(file_path)
                    ingest_file(IngestRequest(file_path, source_name, current_type))
                    summary.files_ingested += 1
                except Exception as e:
                    summary.errors.append(str(e))
        except Exception as e:
            summary.errors.append(str(e))
        return summary

    def _determine_source_type(self, path: Path) -> SourceType:
        ext = path.suffix.lower()
        if ext in {".mp4", ".mov"}: return SourceType.VIDEO_FILE
        if ext in {".mp3", ".wav"}: return SourceType.AUDIO_FILE
        return SourceType.DOCUMENT
