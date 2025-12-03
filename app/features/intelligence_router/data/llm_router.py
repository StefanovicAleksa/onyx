import logging
import torch
import json
from typing import List
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from app.core.config import settings
from app.core.model_lifecycle.manager import ModelLifecycleManager
from app.features.transcription.domain.models import TranscriptionResult
from ..domain.interfaces import IIntelligenceRouter
from ..domain.models import RoutingResult, VisualQuery

logger = logging.getLogger(__name__)

class LlmRouter(IIntelligenceRouter):
    def __init__(self):
        self.model_name = settings.ROUTER_LLM_MODEL
        self.device = settings.ROUTER_DEVICE

    def _load_model_stack(self):
        """
        Loads the 7B Model with 4-bit Quantization (Same tech as Chat/Vision).
        """
        logger.info(f"🧠 Loading Router LLM: {self.model_name} (Int4)...")
        
        # 1. Quantization Config (Crucial for 7B on 12GB VRAM)
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16
        )

        # 2. Load Tokenizer
        tokenizer = AutoTokenizer.from_pretrained(self.model_name, trust_remote_code=True)

        # 3. Load Model
        model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True,
            low_cpu_mem_usage=True
        )
        return model, tokenizer

    def route(self, transcript: TranscriptionResult) -> RoutingResult:
        # 1. Format Transcript for the LLM
        # We group segments to provide context, rather than sending raw lines.
        formatted_transcript = ""
        for seg in transcript.segments:
            start = f"{seg['start']:.1f}"
            end = f"{seg['end']:.1f}"
            formatted_transcript += f"[{start}-{end}] {seg['text']}\n"

        # 2. STRICT System Prompt
        # We tell the model it is a "Video Editor" tasked with cutting costs.
        system_prompt = (
            "You are a strict Video Editor. Your job is to identify ONLY essential visual events "
            "where the speaker specifically references a visual aid.\n\n"
            "STRICT FILTERING RULES:\n"
            "1. ❌ IGNORE 'Talking Heads': If it's just a person speaking without referencing a chart/data, SKIP IT.\n"
            "2. ❌ IGNORE Intro/Outro/Title cards.\n"
            "3. ✅ TRIGGER ONLY if the speaker says phrases like 'look at this graph', 'this chart shows', 'as you can see here'.\n"
            "4. ✅ TRIGGER if the context implies complex visual data is being displayed (e.g., analyzing a price candle, an X-ray, a blueprint).\n\n"
            "OUTPUT FORMAT:\n"
            "Return a raw JSON list of objects: [{'start': float, 'end': float, 'reason': str, 'confidence': float}]\n"
            "Merge adjacent segments that cover the same visual topic."
        )
        
        # We take a chunk of the transcript (Router can handle ~8k tokens easily)
        # For very long videos, you might chunk this, but for 2 hours, the condensed transcript usually fits 
        # or we truncate. 7B handles 32k context, so we are safe.
        user_prompt = f"Transcript:\n{formatted_transcript}\n\nJSON Output:"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        queries = []
        
        # 3. Inference
        with ModelLifecycleManager.resource_lock(self._load_model_stack, "Router_LLM_7B") as (model, tokenizer):
            
            text_input = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            model_inputs = tokenizer([text_input], return_tensors="pt").to(self.device)
            
            generated_ids = model.generate(
                **model_inputs,
                max_new_tokens=2048, # Allow enough space for the JSON list
                temperature=0.1,     # Low temperature for strict adherence
                do_sample=False      # Greedy decoding for consistency
            )
            
            generated_ids_trimmed = [
                out_ids[len(in_ids):] for in_ids, out_ids in zip(model_inputs.input_ids, generated_ids)
            ]
            response_str = tokenizer.batch_decode(generated_ids_trimmed, skip_special_tokens=True)[0]

            logger.debug(f"Router Raw Output: {response_str[:200]}...")

            # 4. Parsing Logic
            try:
                # Clean markdown code blocks if present
                clean_json = response_str.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_json)
                
                if isinstance(data, list):
                    for item in data:
                        # 5. STRICT THRESHOLD
                        # Only accept if the model is >70% confident
                        conf = float(item.get("confidence", 0.0))
                        if conf >= 0.7: 
                            queries.append(VisualQuery(
                                timestamp_start=float(item.get("start", 0.0)),
                                timestamp_end=float(item.get("end", 0.0)),
                                query_text=item.get("reason", "Visual context required"),
                                confidence=conf
                            ))
                        else:
                            logger.info(f"Skipped low confidence trigger ({conf:.2f}): {item.get('reason')}")
                            
            except Exception as e:
                logger.error(f"Failed to parse Router JSON: {e}")
                # Fallback: If parsing fails, we assume no visuals to be safe (rather than crashing)

        return RoutingResult(visual_queries=queries, total_triggers_found=len(queries))