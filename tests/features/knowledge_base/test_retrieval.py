import pytest
import shutil
from app.core.config import settings
from app.features.knowledge_base.service.api import search_knowledge_base
from app.features.knowledge_base.domain.models import KnowledgeChunk, ChunkType
from app.features.knowledge_base.data.chroma_store import ChromaRepository
from app.features.knowledge_base.data.local_embedder import LocalEmbedder

TEST_DB_PATH = settings.BASE_DIR / "data" / "test_chroma_db_retrieval"

@pytest.fixture(scope="module", autouse=True)
def setup_test_data():
    """
    Seeds the DB with specific known facts using real Embeddings.
    """
    original_path = settings.CHROMA_DB_PATH
    settings.CHROMA_DB_PATH = TEST_DB_PATH
    
    if TEST_DB_PATH.exists():
        shutil.rmtree(TEST_DB_PATH)
    TEST_DB_PATH.mkdir(parents=True, exist_ok=True)
    
    # --- SEED DATA ---
    repo = ChromaRepository()
    embedder = LocalEmbedder()
    
    # Fact 1
    text1 = "The project code name is Project Onyx."
    # Fact 2
    text2 = "The server requires an RTX 3060 graphics card."
    
    vecs = embedder.embed_documents([text1, text2])
    
    chunk1 = KnowledgeChunk(
        id="c1", video_id="v1", start_time=0, end_time=1, 
        text_content=text1, chunk_type=ChunkType.TRANSCRIPT, metadata={}
    )
    chunk2 = KnowledgeChunk(
        id="c2", video_id="v1", start_time=2, end_time=3, 
        text_content=text2, chunk_type=ChunkType.TRANSCRIPT, metadata={}
    )
    
    repo.upsert([chunk1, chunk2], vecs)
    
    yield
    
    if TEST_DB_PATH.exists():
        shutil.rmtree(TEST_DB_PATH)
    settings.CHROMA_DB_PATH = original_path

def test_retrieval_semantic_search():
    """
    True Integration Test:
    Queries the DB with a natural language question.
    Verifies that the Vector Search engine (Cosine Similarity) works.
    """
    print("\n🔍 Testing Semantic Retrieval...")
    
    # Query is different from text, but semantically related
    query = "What hardware gpu is needed?"
    
    results = search_knowledge_base(query, limit=1)
    
    assert len(results) > 0
    top_result = results[0]
    
    print(f"   Query: '{query}'")
    print(f"   Match: '{top_result.chunk.text_content}' (Score: {top_result.score:.4f})")
    
    # Check if it retrieved the correct fact
    assert "RTX 3060" in top_result.chunk.text_content
    
    print("✅ Semantic Search Verified.")