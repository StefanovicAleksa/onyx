from dataclasses import dataclass, field
from typing import List, Dict

@dataclass(frozen=True)
class Citation:
    """
    Represents a specific source segment used to answer the query.
    Critical for Legal/Medical auditing.
    """
    video_id: str
    timestamp_start: float
    timestamp_end: float
    text_snippet: str
    score: float

@dataclass(frozen=True)
class ChatRequest:
    """
    Input from the API / Client.
    """
    query: str
    # History format: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
    history: List[Dict[str, str]] = field(default_factory=list)

@dataclass(frozen=True)
class ChatResponse:
    """
    Output to the API / Client.
    """
    answer: str
    citations: List[Citation]
    processing_time: float
    model_used: str