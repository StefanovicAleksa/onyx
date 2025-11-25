import cv2
import logging
import numpy as np
from pathlib import Path
from typing import List
from PIL import Image

logger = logging.getLogger(__name__)

class OpenCVFrameExtractor:
    """
    Extracts a sequence of frames from a video file to simulate 'Video Input' for the LLM.
    """
    
    def extract_clip_samples(self, video_path: Path, start_time: float, end_time: float, fps: int = 1) -> List[Image.Image]:
        """
        Extracts frames uniformly between start_time and end_time.
        
        Args:
            fps: Frames Per Second to extract. 
                 1 is usually sufficient for slides/charts.
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        frames = []
        cap = cv2.VideoCapture(str(video_path))
        
        if not cap.isOpened():
            raise RuntimeError(f"Could not open video: {video_path}")

        try:
            duration = end_time - start_time
            
            # Safety: If duration is tiny (e.g. <1s), grab at least one frame
            if duration <= 0: 
                timestamps = [start_time]
            else:
                # Calculate how many frames we need
                num_frames = int(duration * fps)
                # Ensure at least 1, max 8 (VRAM Safety Cap)
                num_frames = max(1, min(num_frames, 8))
                
                # Generate evenly spaced timestamps
                timestamps = np.linspace(start_time, end_time, num_frames).tolist()

            for ts in timestamps:
                # Jump to specific millisecond
                cap.set(cv2.CAP_PROP_POS_MSEC, ts * 1000)
                success, frame = cap.read()
                
                if success:
                    # Convert BGR (OpenCV) to RGB (PIL/AI)
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frames.append(Image.fromarray(rgb_frame))
                    logger.debug(f"Extracted frame at {ts:.2f}s")
                else:
                    logger.warning(f"Failed to extract frame at {ts:.2f}s")
                    
        finally:
            cap.release()
            
        return frames