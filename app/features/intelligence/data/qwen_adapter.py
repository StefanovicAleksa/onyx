import json
import re
import logging
import torch
from typing import List
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from ..domain.interfaces import ILLMAdapter
from ..domain.models import IntelligenceInsight

logger = logging.getLogger(__name__)


class QwenIntelligenceAdapter(ILLMAdapter):
    def __init__(self, model_path: str = "Qwen/Qwen2.5-7B-Instruct"):
        self.model_path = model_path
        self.model = None
        self.tokenizer = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

    def load(self):
        if self.model is not None:
            return

        logger.info(f"Loading Qwen 2.5 from {self.model_path} in 4-bit...")

        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16
        )

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_path,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True
        )

    def unload(self):
        logger.info("Unloading Qwen from VRAM...")
        self.model = None
        self.tokenizer = None
        torch.cuda.empty_cache()

    def analyze_text(self, text: str) -> List[IntelligenceInsight]:
        prompt = self._build_prompt(text)

        inputs = self.tokenizer([prompt], return_tensors="pt").to(self.device)
        generated_ids = self.model.generate(
            **inputs,
            max_new_tokens=1024,
            temperature=0.1,  # Low temp for high structural integrity
            do_sample=False
        )

        response = self.tokenizer.batch_decode(
            generated_ids[:, inputs.input_ids.shape[1]:],
            skip_special_tokens=True
        )[0]

        return self._parse_response(response)

    def _build_prompt(self, text: str) -> str:
        return f"""<|im_start|>system
You are an expert Legal and Medical Analyst. Analyze the transcript provided.
Extract distinct topics discussed. For each topic, provide:
1. A concise title.
2. A 2-3 sentence summary.
3. Start and End timestamps (derived strictly from the text).
4. A list of key terms (keywords).

Output MUST be a valid JSON list of objects. 
Example Format:
[
  {{"title": "Topic Name", "summary": "Description...", "start_time": 12.5, "end_time": 45.0, "keywords": ["word1", "word2"]}}
]
<|im_end|>
<|im_start|>user
Transcript:
{text}
<|im_end|>
<|im_start|>assistant
"""

    def _parse_response(self, response: str) -> List[IntelligenceInsight]:
        try:
            # Extract JSON block using regex in case of conversational filler
            json_match = re.search(r'\[\s*{.*}\s*]', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(response)

            insights = []
            for item in data:
                insights.append(IntelligenceInsight(
                    title=item.get("title", "Untitled Topic"),
                    summary=item.get("summary", ""),
                    start_time=float(item.get("start_time", 0.0)),
                    end_time=float(item.get("end_time", 0.0)),
                    keywords=item.get("keywords", [])
                ))
            return insights
        except Exception as e:
            logger.error(f"Failed to parse Qwen JSON response: {e}. Raw response: {response}")
            return []