from dataclasses import dataclass, field
from typing import List, Optional
from uuid import UUID

@dataclass
class IntelligenceInsight:
    """Domain representation of a topic extracted by the AI."""
    title: str
    summary: str
    start_time: float
    end_time: float
    keywords: List[str] = field(default_factory=list)
    confidence: float = 1.0
    context_window_id: Optional[UUID] = None

@dataclass
class IntelligenceResult:
    """The collection of insights for a specific processing run."""
    source_id: UUID
    insights: List[IntelligenceInsight]
    processing_time_sec: float