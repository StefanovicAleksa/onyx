import logging
import time
import torch
from typing import List
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from app.core.config import settings
from app.core.model_lifecycle.manager import ModelLifecycleManager
from ..domain.interfaces import IChatModel
from ..domain.models import ChatRequest, ChatResponse, Citation
from app.features.knowledge_base.domain.models import SearchResult

logger = logging.getLogger(__name__)

class QwenChatEngine(IChatModel):
    """
    Concrete implementation using Qwen2.5-14B-Instruct.
    """
    
    def __init__(self):
        self.model_name = settings.CHAT_MODEL_NAME
        self.device = settings.CHAT_DEVICE

    def _load_model_stack(self):
        """Loads Tokenizer and Model in 4-bit mode."""
        logger.info(f"🤖 Loading Chat Model: {self.model_name} (Int4)...")
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16
        )
        tokenizer = AutoTokenizer.from_pretrained(self.model_name, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            quantization_config=bnb_config,
            device_map="auto", 
            trust_remote_code=True,
            low_cpu_mem_usage=True
        )
        return model, tokenizer

    def _format_context(self, chunks: List[SearchResult]) -> str:
        if not chunks: return "No relevant context found."
        context_str = "--- START OF CONTEXT ---\n"
        for i, res in enumerate(chunks):
            context_str += (f"[Source {i+1}]\nVideo ID: {res.chunk.video_id}\n"
                            f"Timestamp: {res.chunk.start_time:.1f}s - {res.chunk.end_time:.1f}s\n"
                            f"Content: {res.chunk.text_content}\n\n")
        context_str += "--- END OF CONTEXT ---\n"
        return context_str

    def generate_response(self, request: ChatRequest, context_chunks: List[SearchResult]) -> ChatResponse:
        """Standard lifecycle-managed generation (Loads -> Generates -> Unloads)"""
        with ModelLifecycleManager.resource_lock(self._load_model_stack, "Qwen_Chat_14B") as (model, tokenizer):
            return self.generate_response_with_loaded_model(request, context_chunks, model, tokenizer)

    def generate_response_with_loaded_model(self, request, context_chunks, model, tokenizer) -> ChatResponse:
        """
        FAST PATH: Generation logic using a pre-loaded model.
        Does NOT trigger lifecycle locks.
        """
        start_time = time.time()
        
        context_block = self._format_context(context_chunks)
        system_prompt = (
            "You are Onyx, a specialized AI assistant. "
            "Answer strictly based on the Context. Cite sources as [Source X].\n"
        )
        
        messages = [{"role": "system", "content": system_prompt}]
        if request.history:
            for msg in request.history[-3:]: 
                messages.append(msg)
            
        user_content = f"Context Data:\n{context_block}\n\nQuestion: {request.query}"
        messages.append({"role": "user", "content": user_content})

        text_input = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        model_inputs = tokenizer([text_input], return_tensors="pt").to(self.device)
        
        generated_ids = model.generate(
            **model_inputs,
            max_new_tokens=512, 
            temperature=0.2,
            do_sample=True
        )
        
        generated_ids_trimmed = [
            out_ids[len(in_ids):] for in_ids, out_ids in zip(model_inputs.input_ids, generated_ids)
        ]
        response_text = tokenizer.batch_decode(generated_ids_trimmed, skip_special_tokens=True)[0]

        citations = []
        for i, res in enumerate(context_chunks):
            if f"[Source {i+1}]" in response_text:
                citations.append(Citation(
                    video_id=res.chunk.video_id,
                    timestamp_start=res.chunk.start_time,
                    timestamp_end=res.chunk.end_time,
                    text_snippet=res.chunk.text_content[:200],
                    score=res.score
                ))

        duration = time.time() - start_time
        return ChatResponse(response_text, citations, duration, self.model_name)