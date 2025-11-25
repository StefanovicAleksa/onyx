import logging
import torch
import json
from typing import List
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
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

    def _load_model_pipeline(self):
        logger.info(f"🧠 Loading Router LLM: {self.model_name}...")
        tokenizer = AutoTokenizer.from_pretrained(self.model_name, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            device_map=self.device,
            torch_dtype=torch.float16,
            trust_remote_code=True
        )
        return pipeline("text-generation", model=model, tokenizer=tokenizer, max_new_tokens=1024, temperature=0.1)

    def route(self, transcript: TranscriptionResult) -> RoutingResult:
        # 1. Format Transcript with Timestamps
        # We convert the segment list into a readable script format for the LLM.
        # Format: "[Start-End] Text"
        formatted_transcript = ""
        for seg in transcript.segments:
            start = f"{seg['start']:.1f}"
            end = f"{seg['end']:.1f}"
            formatted_transcript += f"[{start}-{end}] {seg['text']}\n"

        # 2. Construct Prompt
        # We explicitly ask for start/end times in the JSON output.
        system_prompt = (
            "You are a video analysis director. "
            "Analyze the timestamped transcript below. Identify continuous segments where visual context is required "
            "(e.g., 'drawing on chart', 'showing x-ray', 'pointing at screen'). "
            "Merge adjacent visual segments if they are related. "
            "Return valid JSON list: [{'start': float, 'end': float, 'reason': str, 'confidence': float}]."
        )
        
        user_prompt = f"Transcript:\n{formatted_transcript}\n\nJSON Output:"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        queries = []
        
        with ModelLifecycleManager.resource_lock(self._load_model_pipeline, "Router_LLM") as pipe:
            text_input = pipe.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            outputs = pipe(text_input)
            generated_text = outputs[0]["generated_text"]
            
            # Parsing logic to extract the assistant's response
            if "assistant" in generated_text:
                 response_str = generated_text.split("assistant")[-1].strip()
            else:
                 response_str = generated_text[len(text_input):]

            logger.debug(f"LLM Raw Output: {response_str}")

            try:
                clean_json = response_str.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_json)
                
                if isinstance(data, list):
                    for item in data:
                        queries.append(VisualQuery(
                            timestamp_start=float(item.get("start", 0.0)),
                            timestamp_end=float(item.get("end", 0.0)),
                            query_text=item.get("reason", "Visual context required"),
                            confidence=float(item.get("confidence", 0.5))
                        ))
            except Exception as e:
                logger.error(f"Failed to parse LLM JSON: {e}")

        return RoutingResult(visual_queries=queries, total_triggers_found=len(queries))