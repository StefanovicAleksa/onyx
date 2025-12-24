import logging
from typing import List
from uuid import UUID
from sqlalchemy.orm import joinedload

# External Libs
try:
    import tiktoken
except ImportError:
    tiktoken = None

from app.core.database.connection import SessionLocal
from app.features.transcription.data.sql_models import TranscriptionSegmentModel, TranscriptionModel
from app.features.diarization.data.sql_models import SourceSpeakerModel

from ..domain.models import WindowConfig, ContextWindow
from ..domain.interfaces import ITokenizer
from ..data.sql_models import ContextWindowModel, WindowSegmentLink

logger = logging.getLogger(__name__)


class SimpleTokenizer(ITokenizer):
    """Fallback if tiktoken is missing."""

    def count_tokens(self, text: str) -> int:
        if not text: return 0
        return len(text) // 4


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
    Fetches segments, FORMATS them into a script, calculates sliding windows, and persists them.
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
            # We eagerly load the 'speaker' relationship to avoid N+1 queries during formatting
            segments = (
                db.query(TranscriptionSegmentModel)
                .join(TranscriptionModel, TranscriptionSegmentModel.transcription_id == TranscriptionModel.id)
                .outerjoin(SourceSpeakerModel, TranscriptionSegmentModel.speaker_id == SourceSpeakerModel.id)
                .filter(TranscriptionModel.source_id == source_id)
                .options(joinedload(TranscriptionSegmentModel.speaker))
                .order_by(TranscriptionSegmentModel.start_time)
                .all()
            )

            if not segments:
                logger.warning(f"No transcription segments found for source {source_id}")
                return 0

            logger.info(f"Found {len(segments)} segments. Building formatted windows...")

            # 2. Build Windows (The Algorithm)
            windows = self._build_sliding_windows(segments, config)

            # 3. Persist to DB
            self._save_windows(db, source_id, windows)

            return len(windows)

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        """Converts 125.5 -> 00:02:05"""
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return "{:02d}:{:02d}:{:02d}".format(int(h), int(m), int(s))

    def _format_segment(self, seg: TranscriptionSegmentModel) -> str:
        """
        The Script Formatter.
        Transforms raw data into: "[00:12:45] Dr. Smith: The patient is stable."
        """
        timestamp = self._format_timestamp(seg.start_time)

        # Handle missing speaker (if diarization hasn't run or failed)
        if seg.speaker and seg.speaker.user_label:
            speaker_name = seg.speaker.user_label
        elif seg.speaker and seg.speaker.detected_label:
            speaker_name = seg.speaker.detected_label
        else:
            speaker_name = "Unknown Speaker"

        # The Semantic Format
        return f"[{timestamp}] {speaker_name}: {seg.text}"

    def _build_sliding_windows(self, segments: List[TranscriptionSegmentModel], config: WindowConfig) -> List[
        ContextWindow]:
        windows: List[ContextWindow] = []

        # Pre-calculate formatted text and token counts
        # This is CRITICAL: We must count the tokens of the FINAL format, not just the raw text.
        enriched_segments = []
        for seg in segments:
            formatted_text = self._format_segment(seg)
            count = self.tokenizer.count_tokens(formatted_text)
            enriched_segments.append((seg, count, formatted_text))

        current_window_segments = []
        current_tokens = 0
        window_idx = 0

        i = 0
        while i < len(enriched_segments):
            seg, tokens, fmt_text = enriched_segments[i]

            # Check if adding this segment breaches the target size
            if current_tokens + tokens > config.target_size and current_window_segments:
                # A. Finalize current window
                self._finalize_window(windows, current_window_segments, window_idx)
                window_idx += 1

                # B. Handle Overlap (The "10%" Logic)
                # We look BACKWARDS to fill the overlap quota
                overlap_buffer = []
                overlap_tokens = 0
                back_ptr = i - 1

                while back_ptr >= 0:
                    b_seg, b_tokens, b_fmt = enriched_segments[back_ptr]

                    if overlap_tokens + b_tokens > config.overlap_size and overlap_buffer:
                        break

                    overlap_buffer.insert(0, (b_seg, b_tokens, b_fmt))
                    overlap_tokens += b_tokens
                    back_ptr -= 1

                # C. Start new window with Overlap + Current Segment
                current_window_segments = list(overlap_buffer)
                current_tokens = overlap_tokens

                # Add the segment that caused overflow
                current_window_segments.append((seg, tokens, fmt_text))
                current_tokens += tokens
            else:
                # Just add to current window
                current_window_segments.append((seg, tokens, fmt_text))
                current_tokens += tokens

            i += 1

        # Finalize tail
        if current_window_segments:
            self._finalize_window(windows, current_window_segments, window_idx)

        return windows

    @staticmethod
    def _finalize_window(windows_list, enriched_tuples, idx):
        """
        Joins the formatted strings with newlines to create the "Script".
        """
        # Join with newlines to separate speech turns cleanly
        full_text = "\n".join([t[2] for t in enriched_tuples])
        total_tokens = sum([t[1] for t in enriched_tuples])
        seg_ids = [t[0].id for t in enriched_tuples]

        windows_list.append(ContextWindow(
            window_index=idx,
            full_text=full_text,
            token_count=total_tokens,
            segment_ids=seg_ids
        ))

    @staticmethod
    def _save_windows(db, source_id, windows: List[ContextWindow]):
        """Transactional save of Windows + Links."""
        try:
            for w in windows:
                db_window = ContextWindowModel(
                    source_id=source_id,
                    window_index=w.window_index,
                    text_content=w.full_text,
                    token_count=w.token_count
                )
                db.add(db_window)
                db.flush()

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