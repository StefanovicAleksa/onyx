import logging
import uuid
from typing import List
from app.features.transcription.domain.models import TranscriptionResult
from app.features.vision_analysis.domain.models import VisualContext
from ..domain.models import KnowledgeChunk, ChunkType
from ..data.local_embedder import LocalEmbedder
from ..data.chroma_store import ChromaRepository

logger = logging.getLogger(__name__)

class IngestionService:
    """
    The 'Zipper' that merges Text (Whisper) and Vision (Qwen) into a unified timeline.
    """
    def __init__(self):
        # Dependency Injection (Manual for now)
        self.embedder = LocalEmbedder()
        self.store = ChromaRepository()

    def ingest_video_intelligence(
        self, 
        video_id: str, 
        transcript: TranscriptionResult, 
        visual_contexts: List[VisualContext]
    ) -> int:
        """
        Main processing loop.
        1. Aligns text segments with visual descriptions.
        2. Creates 'Screenplay' style chunks.
        3. Embeds and stores them.
        
        Returns:
            Number of chunks created.
        """
        logger.info(f"🧠 Ingesting intelligence for video: {video_id}")
        
        chunks_to_persist = []
        
        # Iterate through every spoken sentence
        for segment in transcript.segments:
            seg_start = segment['start']
            seg_end = segment['end']
            seg_text = segment['text']
            
            # 1. Find relevant visuals (Intersection of time ranges)
            # A visual context is relevant if it overlaps with this speech segment.
            relevant_visuals = []
            if visual_contexts:
                for vc in visual_contexts:
                    # Check for overlap
                    if (vc.timestamp_start <= seg_end) and (vc.timestamp_end >= seg_start):
                        relevant_visuals.append(vc.description)
            
            # 2. Construct the Content
            # If we have visuals, we format it like a screenplay.
            if relevant_visuals:
                # Join multiple visual descriptions if they exist
                visual_str = " | ".join(relevant_visuals)
                final_text = (
                    f"Timestamp: {seg_start:.1f}s\n"
                    f"Visual Context: {visual_str}\n"
                    f"Spoken Text: \"{seg_text}\""
                )
                c_type = ChunkType.MERGED
            else:
                # Just text
                final_text = f"Timestamp: {seg_start:.1f}s\nSpoken Text: \"{seg_text}\""
                c_type = ChunkType.TRANSCRIPT

            # 3. Create the Chunk Object
            chunk = KnowledgeChunk(
                id=f"{video_id}_{uuid.uuid4().hex[:8]}", # Unique ID
                video_id=video_id,
                start_time=seg_start,
                end_time=seg_end,
                text_content=final_text,
                chunk_type=c_type,
                metadata={"has_visuals": bool(relevant_visuals)}
            )
            chunks_to_persist.append(chunk)

        # 4. Batch Embedding (Efficiency)
        if chunks_to_persist:
            logger.info(f"⚡ Generating vectors for {len(chunks_to_persist)} chunks...")
            text_bodies = [c.text_content for c in chunks_to_persist]
            vectors = self.embedder.embed_documents(text_bodies)
            
            # 5. Persist
            self.store.upsert(chunks_to_persist, vectors)
            
        return len(chunks_to_persist)