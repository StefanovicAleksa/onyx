# File: app/features/knowledge_base/data/local_embedder_v2.py
import logging
import torch
from typing import List
from sentence_transformers import SentenceTransformer
from app.core.config import settings
from ..domain.interfaces import IEmbedder

logger = logging.getLogger(__name__)

class LocalEmbedder(IEmbedder):
    """
    Implementation using the 'BAAI/bge-small-en-v1.5' model.
    
    ARCHITECTURAL CHANGE (RTX 3060 Optimization):
    This model is ~150MB-300MB. With 12GB VRAM, we treat this as a 
    'Resident' model rather than a 'Swappable' model. 
    It stays loaded to ensure Search/Ingestion is instant.
    """
    
    def __init__(self):
        self.model_name = settings.EMBEDDING_MODEL_NAME
        self.device = settings.EMBEDDING_DEVICE 
        
        self.query_instruction = "Represent this sentence for searching relevant passages: "
        
        # Load immediately on instantiation
        logger.info(f"📚 Loading 'The Librarian' ({self.model_name}) on {self.device} (RESIDENT)...")
        self.model = SentenceTransformer(self.model_name, device=self.device)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Converts content chunks into vectors.
        """
        # No resource lock needed anymore. The model is resident.
        # We assume 12GB is enough to hold this + (Whisper OR Vision OR Chat).
        # Whisper Large (~3GB) + Embedder (0.5GB) < 12GB
        # Qwen 14B (~9GB) + Embedder (0.5GB) < 12GB
        
        with torch.no_grad():
            results = self.model.encode(
                texts, 
                batch_size=32, 
                normalize_embeddings=True, 
                show_progress_bar=False,
                device=self.device
            )
            
        return results.tolist()

    def embed_query(self, text: str) -> List[float]:
        """
        Converts a user question into a vector.
        """
        formatted_text = f"{self.query_instruction}{text}"
        
        with torch.no_grad():
            result = self.model.encode(
                [formatted_text], 
                normalize_embeddings=True,
                device=self.device
            )
            return result[0].tolist()