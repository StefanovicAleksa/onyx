import logging
import torch
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
    Works for both 2B and 7B versions seamlessly.
    """
    
    def __init__(self):
        self.model_name = settings.VISION_MODEL_NAME
        self.device = settings.VISION_DEVICE

    def _load_model_stack(self):
        """
        Factory function for Lifecycle Manager.
        """
        logger.info(f"👁️ Loading Vision Model: {self.model_name} (4-bit)...")
        
        # 4-bit Quantization is MANDATORY for 1050 Ti (4GB VRAM)
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16
        )

        # Load Model
        model = Qwen2VLForConditionalGeneration.from_pretrained(
            self.model_name,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True
        )
        
        # Load Processor
        processor = AutoProcessor.from_pretrained(self.model_name, trust_remote_code=True)
        
        return model, processor

    def analyze_segment(self, images: List[Image.Image], query: str, start_time: float, end_time: float) -> VisualContext:
        """
        Feeds the sequence of images to Qwen-VL.
        """
        result_context = None
        
        # STRICT Resource Lock: Kills other models before loading this one
        with ModelLifecycleManager.resource_lock(self._load_model_stack, "Vision_VLM") as (model, processor):
            
            # 1. Build the "Film Strip" Prompt
            content_block = []
            for img in images:
                content_block.append({"type": "image", "image": img})
            
            # We explicitly tell the model these are sequential frames
            text_prompt = (
                f"These images are sequential frames from a video (Time: {start_time}s to {end_time}s). "
                f"Context from Audio: '{query}'. "
                "Describe the visual information shown. "
                "If a graph, document, or scan is visible, interpret the data."
            )
            content_block.append({"type": "text", "text": text_prompt})

            messages = [{"role": "user", "content": content_block}]
            
            # 2. Prepare Inputs
            text_input = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            image_inputs, video_inputs = process_vision_info(messages)
            
            inputs = processor(
                text=[text_input],
                images=image_inputs,
                videos=video_inputs,
                padding=True,
                return_tensors="pt",
            ).to(self.device)

            # 3. Generate
            generated_ids = model.generate(**inputs, max_new_tokens=256)
            
            # 4. Decode
            generated_ids_trimmed = [
                out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
            ]
            output_text = processor.batch_decode(
                generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
            )[0]
            
            logger.info(f"👁️ Vision Analysis: {output_text[:100]}...")
            
            result_context = VisualContext(
                timestamp_start=start_time,
                timestamp_end=end_time,
                description=output_text,
                ocr_text="", # Qwen typically merges OCR into the main description
                confidence=1.0
            )

        return result_context

# Helper required by Qwen2-VL utils
def process_vision_info(messages):
    images = [content['image'] for msg in messages for content in msg['content'] if content['type'] == 'image']
    return images, None