import pytest
import shutil
from app.core.config import settings
from app.features.knowledge_base.data.chroma_store import ChromaRepository
from app.features.knowledge_base.data.local_embedder import LocalEmbedder
from app.features.knowledge_base.domain.models import KnowledgeChunk, ChunkType
from app.features.chat.service.rag_service import ask_onyx

# Shared Test DB
TEST_DB_PATH = settings.BASE_DIR / "data" / "test_chroma_db_chat"

@pytest.fixture(scope="module", autouse=True)
def setup_rag_data():
    """
    Setup a DB with a 'Secret Fact' that the AI could ONLY know 
    if RAG is working correctly.
    """
    original_path = settings.CHROMA_DB_PATH
    settings.CHROMA_DB_PATH = TEST_DB_PATH
    
    if TEST_DB_PATH.exists():
        shutil.rmtree(TEST_DB_PATH)
    TEST_DB_PATH.mkdir(parents=True, exist_ok=True)
    
    # Seed the Secret Fact
    repo = ChromaRepository()
    embedder = LocalEmbedder()
    
    secret_text = "The Golden Key is located under the flower pot in the lobby."
    vecs = embedder.embed_documents([secret_text])
    
    chunk = KnowledgeChunk(
        id="secret_1", video_id="security_cam_1", start_time=100.0, end_time=105.0,
        text_content=secret_text, chunk_type=ChunkType.TRANSCRIPT, metadata={}
    )
    repo.upsert([chunk], vecs)
    
    yield
    
    if TEST_DB_PATH.exists():
        shutil.rmtree(TEST_DB_PATH)
    settings.CHROMA_DB_PATH = original_path

def test_full_rag_pipeline_with_qwen14b():
    """
    CRITICAL INTEGRATION TEST.
    1. Loads the Embedding Model.
    2. Finds the 'Secret Fact' in ChromaDB.
    3. Loads Qwen2.5-14B (4-bit) into VRAM.
    4. Generates an answer using that fact.
    5. Verifies the answer contains the secret.
    """
    print("\n🤖 Starting Full RAG Pipeline Test (High VRAM Usage)...")
    
    question = "Where is the Golden Key hidden?"
    
    # EXECUTE (This will trigger the full model load)
    response = ask_onyx(question)
    
    print(f"\nUser: {question}")
    print(f"Onyx: {response.answer}")
    
    # ASSERTIONS
    # 1. Did it find the info?
    assert "flower pot" in response.answer.lower() or "lobby" in response.answer.lower()
    
    # 2. Did it cite the source? (Requirement for Law/Med)
    assert len(response.citations) > 0
    assert response.citations[0].video_id == "security_cam_1"
    
    print("✅ RAG Pipeline Success: AI used local knowledge to answer.")