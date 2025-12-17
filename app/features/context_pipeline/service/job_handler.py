# File: app/features/context_pipeline/service/job_handler.py
import logging
from uuid import UUID
from app.core.database.connection import SessionLocal
from app.core.jobs.models import JobModel, JobStatus
from .orchestrator import ContextOrchestrator
from ..domain.models import WindowConfig

logger = logging.getLogger(__name__)

class ContextPipelineHandler:
    """
    Worker for JOB_TYPE.PIPELINE_RUN (or specialized CONTEXT_PREP job).
    Prepares the data for downstream AI tasks.
    """
    
    def handle(self, source_id: UUID, params: dict) -> dict:
        logger.info(f"Processing Context Pipeline for Source: {source_id}")
        
        # 1. Parse Config
        # Allow overriding defaults via job params
        limit = params.get("context_window_limit", 8192)
        safe_ratio = params.get("safe_buffer_ratio", 0.90)
        overlap_ratio = params.get("overlap_ratio", 0.10)
        
        config = WindowConfig(
            context_window_limit=limit,
            safe_buffer_ratio=safe_ratio,
            overlap_ratio=overlap_ratio
        )
        
        # 2. Run Logic
        orchestrator = ContextOrchestrator()
        count = orchestrator.process_source(source_id, config)
        
        logger.info(f"Context Pipeline Complete. Created {count} windows.")
        
        return {
            "windows_created": count,
            "strategy": "sliding_window_90_10"
        }