# File: app/features/context_pipeline/domain/models.py
from dataclasses import dataclass, field
from typing import List, Optional
from uuid import UUID

@dataclass
class WindowConfig:
    """
    Configuration for the Sliding Window Algorithm.
    Defaults to Qwen 2.5 7B settings (approx 8k-32k context).
    """
    context_window_limit: int = 8192  # Total Token Limit
    safe_buffer_ratio: float = 0.90   # Use 90% of limit (leave room for sys prompt)
    overlap_ratio: float = 0.10       # Overlap 10% of the PREVIOUS window
    
    @property
    def target_size(self) -> int:
        return int(self.context_window_limit * self.safe_buffer_ratio)

    @property
    def overlap_size(self) -> int:
        return int(self.context_window_limit * self.overlap_ratio)

@dataclass
class ContextWindow:
    """
    A prepared chunk of text ready for the LLM.
    Contains the text and the keys to find where it came from.
    """
    window_index: int
    full_text: str
    token_count: int
    # The ordered list of Segment UUIDs that make up this text
    segment_ids: List[UUID] = field(default_factory=list)