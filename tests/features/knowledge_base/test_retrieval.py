import pytest
from unittest.mock import MagicMock, patch
from app.features.knowledge_base.service.api import search_knowledge_base
from app.features.knowledge_base.domain.models import ChunkType, KnowledgeChunk, SearchResult

def test_retrieval_logic():
    """
    Verifies that the search API:
    1. Embeds the query using the Librarian.
    2. Queries the Filing Cabinet (ChromaDB).
    3. Returns valid Domain Objects.
    """
    query = "Show me the profit graph"
    mock_query_vector = [0.9] * 384
    
    # Mock Result Object from DB Layer
    mock_search_result = SearchResult(
        chunk=KnowledgeChunk(
            id="test_id",
            video_id="test_vid_1",
            start_time=5.0,
            end_time=10.0,
            text_content="Visual: Red Graph | Text: Look at this",
            chunk_type=ChunkType.MERGED
        ),
        score=0.15
    )

    # Patch the dependencies inside the API module
    with patch("app.features.knowledge_base.service.api.LocalEmbedder") as MockEmbedder, \
         patch("app.features.knowledge_base.service.api.ChromaRepository") as MockStore:
        
        # Setup Mocks
        mock_embedder_instance = MockEmbedder.return_value
        mock_embedder_instance.embed_query.return_value = mock_query_vector
        
        mock_store_instance = MockStore.return_value
        mock_store_instance.search.return_value = [mock_search_result]
        
        # Execute
        results = search_knowledge_base(query, limit=3)
        
        # Verify
        mock_embedder_instance.embed_query.assert_called_once_with(query)
        mock_store_instance.search.assert_called_once_with(mock_query_vector, limit=3)
        
        assert len(results) == 1
        assert results[0].chunk.video_id == "test_vid_1"
        assert results[0].score == 0.15
        
        print("✅ Retrieval Logic Verified: Query flowed to DB correctly.")