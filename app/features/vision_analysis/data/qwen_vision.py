import logging
import torch
import gc
from typing import List
from PIL import Image
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig
from app.core.config import settings
from app.core.model_lifecycle.manager import ModelLifecycleManager
from ..domain.models import VisualContext

logger = logging.getLogger(__name__)

class QwenVisionAnalyzer:
    """
    Implementation of the Vision Model (Qwen2-VL).
    Optimized for V2:
    - Smart Memory Management (No aggressive empty_cache)
    - Auto-Resizing to 768px (Prevents OOM)
    """
    
    def __init__(self):
        self.model_name = settings.VISION_MODEL_NAME
        self.device = settings.VISION_DEVICE

    def _load_model_stack(self):
        """Factory function for Lifecycle Manager."""
        logger.info(f"👁️ Loading Vision Model: {self.model_name} (4-bit)...")
        
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16
        )

        model = Qwen2VLForConditionalGeneration.from_pretrained(
            self.model_name,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True
        )
        
        processor = AutoProcessor.from_pretrained(self.model_name, trust_remote_code=True)
        
        return model, processor

    def _safe_resize(self, img: Image.Image, max_dim: int = 768) -> Image.Image:
        """
        Downscales high-res images to fit in VRAM.
        768px is the 'Sweet Spot' for 12GB VRAM cards.
        """
        width, height = img.size
        if max(width, height) <= max_dim:
            return img
            
        ratio = max_dim / max(width, height)
        new_size = (int(width * ratio), int(height * ratio))
        return img.resize(new_size, Image.Resampling.LANCZOS)

    def analyze_batch(self, segments_data: List[dict]) -> List[VisualContext]:
        results = []
        
        # SINGLE LOCK for the entire batch
        with ModelLifecycleManager.resource_lock(self._load_model_stack, "Vision_VLM_Batch") as (model, processor):
            
            total = len(segments_data)
            logger.info(f"🚀 Starting Fast Batch Inference for {total} segments...")

            for i, seg in enumerate(segments_data):
                images = seg['images']
                query = seg['query']
                start = seg['start']
                end = seg['end']
                
                logger.info(f"   -> Processing Batch Item {i+1}/{total} ({start}s - {end}s)")

                try:
                    # 1. Resize Images (Crucial for VRAM Safety)
                    processed_images = [self._safe_resize(img) for img in images]

                    # 2. Build Prompt
                    content_block = []
                    for img in processed_images:
                        content_block.append({"type": "image", "image": img})
                    
                    text_prompt = (
                        f"Video Frame Sequence ({start}s - {end}s). "
                        f"Context: '{query}'. "
                        "Describe the visual information shown. interpret graphs or text if visible."
                    )
                    content_block.append({"type": "text", "text": text_prompt})
                    messages = [{"role": "user", "content": content_block}]

                    # 3. Prepare Inputs
                    text_input = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                    image_inputs, video_inputs = process_vision_info(messages)
                    
                    inputs = processor(
                        text=[text_input],
                        images=image_inputs,
                        videos=video_inputs,
                        padding=True,
                        return_tensors="pt",
                    ).to(self.device)

                    # 4. Generate
                    generated_ids = model.generate(**inputs, max_new_tokens=256)
                    
                    # 5. Decode
                    generated_ids_trimmed = [
                        out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
                    ]
                    output_text = processor.batch_decode(
                        generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
                    )[0]
                    
                    results.append(VisualContext(
                        timestamp_start=start,
                        timestamp_end=end,
                        description=output_text,
                        ocr_text="",
                        confidence=1.0
                    ))

                    # 6. FAST CLEANUP:
                    # We delete the python references so PyTorch's internal allocator knows this memory is free.
                    # We do NOT call empty_cache() here; we let PyTorch reuse the memory for the next image.
                    del inputs
                    del generated_ids
                    del processed_images

                except torch.cuda.OutOfMemoryError:
                    # 7. EMERGENCY CLEANUP:
                    # Only if we actually hit the wall do we pay the cost of a full scrub.
                    logger.warning(f"⚠️ VRAM OOM on segment {i+1}. Flushing cache and skipping.")
                    torch.cuda.empty_cache()
                    gc.collect()
                    continue
                    
                except Exception as e:
                    logger.error(f"❌ Failed to process segment {start}-{end}: {e}")
                    continue
            
            # Final scrub before returning control to Chat/Other models
            logger.info("🧹 Batch complete. Releasing VRAM.")
            torch.cuda.empty_cache()
            gc.collect()
            
        return results

    def analyze_segment(self, images: List[Image.Image], query: str, start_time: float, end_time: float) -> VisualContext:
        """Legacy wrapper."""
        batch_input = [{'images': images, 'query': query, 'start': start_time, 'end': end_time}]
        results = self.analyze_batch(batch_input)
        return results[0] if results else None

# Helper required by Qwen2-VL utils
def process_vision_info(messages):
    images = [content['image'] for msg in messages for content in msg['content'] if content['type'] == 'image']
    return images, None