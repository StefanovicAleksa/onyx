from pathlib import Path
from typing import List
import logging
from ..domain.models import VisualContext
from ..data.frame_extractor import OpenCVFrameExtractor
from ..data.qwen_vision import QwenVisionAnalyzer

logger = logging.getLogger(__name__)

def analyze_video_segment(video_path: Path, start: float, end: float, query: str) -> VisualContext:
    """
    Main Entrypoint:
    1. Extracts a sequence of frames (Clip).
    2. Uses Qwen2-VL to describe the action/content.
    """
    # 1. Extract Sequence (CPU)
    extractor = OpenCVFrameExtractor()
    # 1 FPS is a good balance for slides/medical scans.
    # For fast action, we might increase this later.
    images = extractor.extract_clip_samples(video_path, start, end, fps=1)
    
    if not images:
        logger.warning(f"No frames extracted for segment {start}-{end}")
        return None

    # 2. Analyze Sequence (GPU)
    analyzer = QwenVisionAnalyzer()
    result = analyzer.analyze_segment(images, query, start, end)
    
    return result