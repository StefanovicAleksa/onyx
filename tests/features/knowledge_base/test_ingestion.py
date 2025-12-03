import pytest
import shutil
from app.core.config import settings
from app.features.transcription.domain.models import TranscriptionResult
from app.features.vision_analysis.domain.models import VisualContext
from app.features.knowledge_base.service.ingestion_service import IngestionService
from app.features.knowledge_base.data.chroma_store import ChromaRepository

# We use a separate collection or DB path for tests to avoid messing up production data
TEST_DB_PATH = settings.BASE_DIR / "data" / "test_chroma_db"

@pytest.fixture(scope="module", autouse=True)
def setup_teardown_db():
    """
    Sets up a temporary ChromaDB environment for the Integration Test.
    """
    # 1. Override Global Config temporarily
    original_path = settings.CHROMA_DB_PATH
    settings.CHROMA_DB_PATH = TEST_DB_PATH
    
    # Clean start
    if TEST_DB_PATH.exists():
        shutil.rmtree(TEST_DB_PATH)
    TEST_DB_PATH.mkdir(parents=True, exist_ok=True)
    
    yield
    
    # 2. Cleanup
    if TEST_DB_PATH.exists():
        shutil.rmtree(TEST_DB_PATH)
    
    # Restore Config
    settings.CHROMA_DB_PATH = original_path

def test_ingestion_integration_real():
    """
    True Integration Test:
    1. Takes raw Transcription and Visual objects.
    2. Uses REAL LocalEmbedder (BAAI/bge-small) to generate vectors.
    3. Writes to REAL ChromaDB on disk.
    4. Verifies data persistence.
    """
    print("\n🧪 Starting Real Ingestion Test (GPU Required for Embeddings)...")
    
    # 1. Prepare Data
    transcript = TranscriptionResult(
        text="Full text",
        language="en",
        processing_time=1.0,
        segments=[
            {"start": 0.0, "end": 5.0, "text": "This is a test of the emergency system."},
            {"start": 5.0, "end": 10.0, "text": "We are testing the GPU memory."}
        ]
    )
    
    visuals = [
        VisualContext(
            timestamp_start=6.0, 
            timestamp_end=9.0, 
            description="A computer screen showing a terminal with green text.",
            ocr_text="MEM: 12GB OK",
            confidence=0.99
        )
    ]
    
    # 2. Execute Service (No Mocks!)
    service = IngestionService()
    count = service.ingest_video_intelligence("integration_test_vid", transcript, visuals)
    
    # 3. Verify in DB
    assert count == 2, f"Expected 2 chunks to be ingested, got {count}"
    
    # Open DB manually to check
    repo = ChromaRepository()
    # We query by video_id to ensure metadata filter works
    results = repo.collection.get(where={"video_id": "integration_test_vid"})
    
    stored_ids = results["ids"]
    stored_metas = results["metadatas"]
    
    assert len(stored_ids) == 2
    print("✅ Verified 2 chunks persisted in ChromaDB.")
    
    # Check if visuals were merged
    visual_chunk = next((m for m in stored_metas if m["has_visuals"] is True), None)
    assert visual_chunk is not None, "Failed to persist visual metadata."
    
    print("✅ Real Ingestion Logic Verified.")