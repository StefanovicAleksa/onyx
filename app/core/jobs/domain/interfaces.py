from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from uuid import UUID

from app.core.db_models import JobModel
from app.core.enums import JobType
from .models import JobSubmission

class IJobRepository(ABC):
    """
    Contract for Job persistence.
    Abstracts the logic of finding 'Sibling Jobs' (Compute Deduplication).
    """
    
    @abstractmethod
    def find_completed_sibling(self, 
                               file_id: UUID, 
                               job_type: JobType, 
                               payload: Dict[str, Any]) -> Optional[JobModel]:
        """
        Finds a COMPLETED job that ran on the SAME physical file (file_id)
        with the EXACT same parameters (payload).
        """
        pass

    @abstractmethod
    def create_job(self, submission: JobSubmission, is_cached: bool = False, cached_meta: dict = None) -> UUID:
        """
        Creates a new Job record.
        If is_cached is True, creates it as COMPLETED with cached_meta.
        If is_cached is False, creates it as PENDING.
        """
        pass
    
    @abstractmethod
    def get_file_id_for_source(self, source_id: UUID) -> Optional[UUID]:
        """
        Helper to resolve a Source ID to its physical File ID.
        """
        pass
