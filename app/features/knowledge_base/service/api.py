import logging
from typing import List
from app.features.transcription.domain.models import TranscriptionResult
from app.features.vision_analysis.domain.models import VisualContext
from ..domain.models import SearchResult
from ..data.local_embedder import LocalEmbedder
from ..data.chroma_store import ChromaRepository
from .ingestion_service import IngestionService

logger = logging.getLogger(__name__)

# --- WRITE PATH (Ingestion) ---

def ingest_processed_video(
    video_filename: str, 
    transcript: TranscriptionResult, 
    visuals: List[VisualContext]
) -> int:
    """
    Saves the processed intelligence of a video into the Knowledge Base.
    """
    service = IngestionService()
    count = service.ingest_video_intelligence(video_filename, transcript, visuals)
    return count

# --- READ PATH (Retrieval) ---

def search_knowledge_base(query: str, limit: int = 5) -> List[SearchResult]:
    """
    Searches the Knowledge Base for context relevant to the user's query.
    Handles the embedding generation and DB lookup.
    """
    logger.info(f"🔍 Searching Knowledge Base for: '{query}'")
    
    # 1. Embed Query (using the Librarian)
    embedder = LocalEmbedder()
    query_vec = embedder.embed_query(query)
    
    # 2. Search DB (using the Filing Cabinet)
    store = ChromaRepository()
    results = store.search(query_vec, limit=limit)
    
    logger.info(f"✅ Found {len(results)} relevant contexts.")
    return results