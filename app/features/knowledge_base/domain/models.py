from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List

class ChunkType(Enum):
    TRANSCRIPT = "transcript"           # Pure audio transcript
    VISUAL = "visual_description"       # Pure visual description
    MERGED = "merged_context"           # The "Screenplay" format (Audio + Visual)

@dataclass(frozen=True)
class KnowledgeChunk:
    """
    The atomic unit of information stored in the Vector DB.
    
    Attributes:
        id: Unique identifier (e.g., 'vid_123_seg_45').
        video_id: The filename/hash of the source video.
        start_time: When this event started (seconds).
        end_time: When this event ended (seconds).
        text_content: The actual text to be vectorized and searched.
        chunk_type: The source of this information.
        metadata: Arbitrary extra data (confidence scores, speaker names).
    """
    id: str
    video_id: str
    start_time: float
    end_time: float
    text_content: str
    chunk_type: ChunkType
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SearchResult:
    """
    The result returned to the application after a search.
    Wraps the Chunk with a similarity score.
    """
    chunk: KnowledgeChunk
    score: float            # Similarity distance (Lower is usually better/closer)