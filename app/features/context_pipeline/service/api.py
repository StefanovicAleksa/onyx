# File: app/features/context_pipeline/service/api.py
from uuid import UUID
from ..domain.models import WindowConfig
from .orchestrator import ContextOrchestrator

def create_context_windows(source_id: str, context_limit: int = 8192) -> int:
    """
    Public API: Generates sliding windows for a source.
    Returns the number of windows created.
    """
    config = WindowConfig(context_window_limit=context_limit)
    orchestrator = ContextOrchestrator()
    return orchestrator.process_source(UUID(source_id), config)