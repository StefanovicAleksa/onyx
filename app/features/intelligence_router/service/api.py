import logging
from app.features.transcription.domain.models import TranscriptionResult
from ..domain.models import RoutingResult
from ..data.llm_router import LlmRouter 

logger = logging.getLogger(__name__)

def route_transcript(transcript: TranscriptionResult) -> RoutingResult:
    """
    Main Entrypoint: Analyzes a transcript to find visual cues.
    """
    # The router will automatically pick the model defined in settings
    router = LlmRouter()
    
    logger.info("🧠 Routing transcript for visual intelligence...")
    result = router.route(transcript)
    
    logger.info(f"🧠 Routing complete. Found {result.total_triggers_found} visual triggers.")
    return result