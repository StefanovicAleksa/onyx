# File: app/features/context_pipeline/service/orchestrator.py
import logging
from typing import List, Tuple
from uuid import UUID

# External Libs (Tiktoken is standard for local estimation)
try:
    import tiktoken
except ImportError:
    tiktoken = None

from app.core.database.connection import SessionLocal
from app.features.storage.data.sql_models import SourceModel
from app.features.transcription.data.sql_models import TranscriptionSegmentModel, TranscriptionModel

from ..domain.models import WindowConfig, ContextWindow
from ..domain.interfaces import ITokenizer
from ..data.sql_models import ContextWindowModel, WindowSegmentLink

logger = logging.getLogger(__name__)

class SimpleTokenizer(ITokenizer):
    """Fallback if tiktoken is missing."""
    def count_tokens(self, text: str) -> int:
        if not text: return 0
        return len(text) // 4  # Rough heuristic

class TiktokenTokenizer(ITokenizer):
    """Production-grade tokenizer."""
    def __init__(self, model="gpt-4"):
        self.enc = tiktoken.encoding_for_model(model)
    def count_tokens(self, text: str) -> int:
        if not text: return 0
        return len(self.enc.encode(text))

class ContextOrchestrator:
    """
    The Brains.
    Fetches segments, calculates sliding windows, and persists them.
    """
    def __init__(self):
        if tiktoken:
            self.tokenizer = TiktokenTokenizer()
        else:
            logger.warning("Tiktoken not found. Using rough token estimation.")
            self.tokenizer = SimpleTokenizer()

    def process_source(self, source_id: UUID, config: WindowConfig) -> int:
        """
        Main entry point. Returns number of windows created.
        """
        logger.info(f"ContextPipeline: Processing Source {source_id} with limit {config.context_window_limit}")
        
        with SessionLocal() as db:
            # 1. Fetch ALL Segments (Sorted by time)
            # FIXED: Explicit Join and Filter on TranscriptionModel
            segments = (
                db.query(TranscriptionSegmentModel)
                .join(TranscriptionModel, TranscriptionSegmentModel.transcription_id == TranscriptionModel.id)
                .filter(TranscriptionModel.source_id == source_id)
                .order_by(TranscriptionSegmentModel.start_time)
                .all()
            )
            
            if not segments:
                logger.warning(f"No transcription segments found for source {source_id}")
                return 0

            logger.info(f"Found {len(segments)} segments. Building windows...")

            # 2. Build Windows (The Algorithm)
            windows = self._build_sliding_windows(segments, config)
            
            # 3. Persist to DB
            self._save_windows(db, source_id, windows)
            
            return len(windows)

    def _build_sliding_windows(self, segments: List[TranscriptionSegmentModel], config: WindowConfig) -> List[ContextWindow]:
        windows: List[ContextWindow] = []
        
        # Pre-calculate token counts for performance (CPU bound)
        enriched_segments = []
        for seg in segments:
            text = seg.text if seg.text else ""
            count = self.tokenizer.count_tokens(text)
            enriched_segments.append((seg, count))

        current_window_segments = []
        current_tokens = 0
        window_idx = 0
        
        i = 0
        while i < len(enriched_segments):
            seg, tokens = enriched_segments[i]
            
            # Check if adding this segment breaches the target size
            if current_tokens + tokens > config.target_size and current_window_segments:
                # A. Finalize current window
                self._finalize_window(windows, current_window_segments, window_idx)
                window_idx += 1
                
                # B. Handle Overlap (The "10%" Logic)
                # We need to look BACKWARDS from 'i' to find segments that fit the overlap size
                overlap_buffer = []
                overlap_tokens = 0
                back_ptr = i - 1
                
                # Walk back until we fill the overlap quota
                while back_ptr >= 0:
                    b_seg, b_tokens = enriched_segments[back_ptr]
                    # Check if this single segment is already too big, or if adding it exceeds overlap
                    # Note: We prioritize keeping at least one segment if possible, 
                    # but strictly we stop if we cross overlap_size.
                    if overlap_tokens + b_tokens > config.overlap_size and overlap_buffer:
                        break 
                    
                    overlap_buffer.insert(0, (b_seg, b_tokens)) # Prepend to keep order
                    overlap_tokens += b_tokens
                    back_ptr -= 1
                
                # C. Start new window with Overlap + Current Segment
                current_window_segments = list(overlap_buffer)
                current_tokens = overlap_tokens
                
                # Now add the segment that caused the overflow
                current_window_segments.append((seg, tokens))
                current_tokens += tokens
            else:
                # Just add to current window
                current_window_segments.append((seg, tokens))
                current_tokens += tokens
            
            i += 1
            
        # Finalize the last window (tail)
        if current_window_segments:
            self._finalize_window(windows, current_window_segments, window_idx)

        return windows

    def _finalize_window(self, windows_list, segment_tuples, idx):
        """Helper to create the ContextWindow object from accumulated segments."""
        full_text = " ".join([s[0].text for s in segment_tuples])
        total_tokens = sum([s[1] for s in segment_tuples])
        seg_ids = [s[0].id for s in segment_tuples]
        
        windows_list.append(ContextWindow(
            window_index=idx,
            full_text=full_text,
            token_count=total_tokens,
            segment_ids=seg_ids
        ))

    def _save_windows(self, db, source_id, windows: List[ContextWindow]):
        """Transactional save of Windows + Links."""
        try:
            for w in windows:
                # Create Window Record
                db_window = ContextWindowModel(
                    source_id=source_id,
                    window_index=w.window_index,
                    text_content=w.full_text,
                    token_count=w.token_count
                )
                db.add(db_window)
                db.flush() # Get ID
                
                # Create Links (Provenance)
                for seg_id in w.segment_ids:
                    link = WindowSegmentLink(
                        window_id=db_window.id,
                        transcription_segment_id=seg_id
                    )
                    db.add(link)
            
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to save context windows: {e}")
            raise e