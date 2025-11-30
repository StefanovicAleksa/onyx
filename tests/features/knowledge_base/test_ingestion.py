import pytest
from unittest.mock import MagicMock, patch
from app.features.transcription.domain.models import TranscriptionResult
from app.features.vision_analysis.domain.models import VisualContext
from app.features.knowledge_base.service.ingestion_service import IngestionService
from app.features.knowledge_base.domain.models import ChunkType

def test_ingestion_merging_logic():
    """
    Verifies that 'The Zipper' correctly merges text and vision
    when timestamps overlap.
    """
    # 1. Mock Data
    transcript = TranscriptionResult(
        text="Full text",
        language="en",
        processing_time=1.0,
        segments=[
            {"start": 0.0, "end": 5.0, "text": "Hello world"},
            {"start": 5.0, "end": 10.0, "text": "Look at this graph"}, # Should merge
            {"start": 10.0, "end": 15.0, "text": "Goodbye"}
        ]
    )
    
    visuals = [
        VisualContext(
            timestamp_start=6.0, 
            timestamp_end=9.0, 
            description="A red bar chart showing profit",
            ocr_text="Profit +10%",
            confidence=0.99
        )
    ]
    
    # 2. Mock Dependencies
    # We patch the classes imported INSIDE ingestion_service.py
    with patch("app.features.knowledge_base.service.ingestion_service.LocalEmbedder") as MockEmbedder, \
         patch("app.features.knowledge_base.service.ingestion_service.ChromaRepository") as MockStore:
        
        # Setup Mocks
        mock_embedder_instance = MockEmbedder.return_value
        # Return fake vectors (list of lists)
        mock_embedder_instance.embed_documents.return_value = [[0.1]*384] * 3 
        
        mock_store_instance = MockStore.return_value

        # 3. Execute
        service = IngestionService()
        count = service.ingest_video_intelligence("test_vid_1", transcript, visuals)
        
        # 4. Verify
        assert count == 3
        
        # Check what was sent to the DB
        # The store.upsert was called once with a list of chunks
        inserted_chunks = mock_store_instance.upsert.call_args[0][0]
        
        # Chunk 0: "Hello world" (No Visuals)
        assert inserted_chunks[0].chunk_type == ChunkType.TRANSCRIPT
        
        # Chunk 1: "Look at this graph" (Visuals!)
        merged_chunk = inserted_chunks[1]
        assert merged_chunk.chunk_type == ChunkType.MERGED
        assert "A red bar chart" in merged_chunk.text_content
        assert "Look at this graph" in merged_chunk.text_content
        
        # Chunk 2: "Goodbye" (No Visuals)
        assert inserted_chunks[2].chunk_type == ChunkType.TRANSCRIPT
        
        print("✅ Ingestion Logic Verified: Text and Vision merged correctly.")