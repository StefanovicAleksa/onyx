import chromadb
import logging
import uuid
from typing import List
from app.core.config import settings
from ..domain.interfaces import IVectorStore
from ..domain.models import KnowledgeChunk, SearchResult, ChunkType

logger = logging.getLogger(__name__)

class ChromaRepository(IVectorStore):
    """
    Local implementation of the Vector Store using ChromaDB.
    Persists data to disk at 'app/data/chroma_db'.
    """
    
    def __init__(self):
        # Ensure the data directory exists
        settings.CHROMA_DB_PATH.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"📂 Initializing ChromaDB at {settings.CHROMA_DB_PATH}")
        self.client = chromadb.PersistentClient(path=str(settings.CHROMA_DB_PATH))
        
        # Get or Create the main collection
        self.collection = self.client.get_or_create_collection(
            name="onyx_knowledge_main",
            metadata={"hnsw:space": "cosine"} # Use Cosine Similarity
        )

    def upsert(self, chunks: List[KnowledgeChunk], vectors: List[List[float]]) -> None:
        if not chunks:
            return

        # Unwrap Domain Objects into parallel lists for Chroma
        ids = [c.id for c in chunks]
        documents = [c.text_content for c in chunks]
        
        # Build Metadata Dicts (The "Paperclip")
        metadatas = []
        for c in chunks:
            meta = {
                "video_id": c.video_id,
                "start": c.start_time,
                "end": c.end_time,
                "type": c.chunk_type.value
            }
            # Flatten any extra metadata into the root dict
            if c.metadata:
                for k, v in c.metadata.items():
                    # Chroma only supports str, int, float, bool. Convert complex types to str.
                    if not isinstance(v, (str, int, float, bool)):
                        meta[k] = str(v)
                    else:
                        meta[k] = v
            metadatas.append(meta)

        # Write to DB
        self.collection.upsert(
            ids=ids,
            embeddings=vectors,
            documents=documents,
            metadatas=metadatas
        )
        logger.info(f"💾 Indexed {len(chunks)} items into ChromaDB.")

    def search(self, query_vector: List[float], limit: int = 5) -> List[SearchResult]:
        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=limit
        )
        
        domain_results = []
        
        # Chroma returns lists of lists (batch format)
        if not results['ids']:
            return []

        ids = results['ids'][0]
        docs = results['documents'][0]
        metas = results['metadatas'][0]
        distances = results['distances'][0]

        for i in range(len(ids)):
            meta = metas[i]
            
            # Reconstruct Domain Object
            chunk = KnowledgeChunk(
                id=ids[i],
                video_id=meta.get('video_id', 'unknown'),
                start_time=float(meta.get('start', 0.0)),
                end_time=float(meta.get('end', 0.0)),
                text_content=docs[i],
                chunk_type=ChunkType(meta.get('type', 'transcript'))
            )
            
            # Create Result
            domain_results.append(SearchResult(
                chunk=chunk,
                score=distances[i]
            ))
            
        return domain_results