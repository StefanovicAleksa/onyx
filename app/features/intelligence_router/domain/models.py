from dataclasses import dataclass
from typing import List

@dataclass(frozen=True)
class VisualQuery:
    """
    Defines a time range in the video that requires visual analysis.
    """
    timestamp_start: float
    timestamp_end: float
    query_text: str       # "User is drawing on the sales graph"
    confidence: float

@dataclass(frozen=True)
class RoutingResult:
    visual_queries: List[VisualQuery]
    total_triggers_found: int