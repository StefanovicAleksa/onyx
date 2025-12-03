from pathlib import Path
from typing import List, Dict, Any
import logging
from ..domain.models import VisualContext
from ..data.frame_extractor import OpenCVFrameExtractor
from ..data.qwen_vision import QwenVisionAnalyzer

logger = logging.getLogger(__name__)

def analyze_video_segments_batch(video_path: Path, queries: List[Any]) -> List[VisualContext]:
    """
    Optimized Entrypoint: Extracts all frames first, then loads model ONCE to process all.
    
    Args:
        video_path: Path to video.
        queries: List of VisualQuery objects (from Router).
    """
    extractor = OpenCVFrameExtractor()
    analyzer = QwenVisionAnalyzer()
    
    batch_input = []
    
    # 1. Extract All Frames (CPU Work - Cheap)
    logger.info(f"📸 Pre-extracting frames for {len(queries)} segments...")
    for q in queries:
        images = extractor.extract_clip_samples(video_path, q.timestamp_start, q.timestamp_end, fps=1)
        if images:
            batch_input.append({
                'images': images,
                'query': q.query_text,
                'start': q.timestamp_start,
                'end': q.timestamp_end
            })
            
    if not batch_input:
        return []

    # 2. Run Batch Analysis (GPU Work - Expensive)
    # This triggers the SINGLE loading event
    logger.info(f"🚀 Batch processing {len(batch_input)} segments on GPU...")
    results = analyzer.analyze_batch(batch_input)
    
    return results

def analyze_video_segment(video_path: Path, start: float, end: float, query: str) -> VisualContext:
    """Legacy single-call wrapper."""
    extractor = OpenCVFrameExtractor()
    images = extractor.extract_clip_samples(video_path, start, end, fps=1)
    if not images:
        return None
        
    analyzer = QwenVisionAnalyzer()
    # We wrap it in a list to use the batch optimization implicitly
    results = analyzer.analyze_batch([{
        'images': images, 'query': query, 'start': start, 'end': end
    }])
    return results[0] if results else None