import logging
from typing import List, Dict, Generator
from contextlib import contextmanager
from app.features.knowledge_base.service.api import search_knowledge_base
from ..data.qwen_engine import QwenChatEngine
from ..domain.models import ChatRequest, ChatResponse
from app.core.model_lifecycle.manager import ModelLifecycleManager

logger = logging.getLogger(__name__)

class ActiveChatSession:
    """Helper class to interact with a loaded model."""
    def __init__(self, engine, model, tokenizer):
        self.engine = engine
        self.model = model
        self.tokenizer = tokenizer
        
    def ask(self, query: str, history: List[Dict[str, str]] = None) -> ChatResponse:
        if history is None:
            history = []
            
        # 1. Retrieval (Cheap)
        context_results = search_knowledge_base(query, limit=4)
        
        # 2. Generation (Fast - Model already loaded)
        request = ChatRequest(query=query, history=history)
        
        response = self.engine.generate_response_with_loaded_model(
            request, context_results, self.model, self.tokenizer
        )
        return response

@contextmanager
def chat_session() -> Generator[ActiveChatSession, None, None]:
    """
    Context Manager that holds the Qwen 14B model in memory.
    
    Usage:
        with chat_session() as chat:
            chat.ask("Hello") # Instant
            chat.ask("Next")  # Instant
    """
    engine = QwenChatEngine()
    
    # Manually acquire lock and HOLD IT for the duration of the 'with' block
    logger.info("🟢 Starting Persistent Chat Session (Loading 14B Model)...")
    with ModelLifecycleManager.resource_lock(engine._load_model_stack, "Qwen_Chat_Session") as (model, tokenizer):
        
        session = ActiveChatSession(engine, model, tokenizer)
        yield session
        
    logger.info("🔴 Ending Persistent Chat Session (Unloading Model)...")

# Standard single-shot entrypoint (Legacy)
def ask_onyx(query: str, history: List[Dict[str, str]] = None) -> ChatResponse:
    with chat_session() as session:
        return session.ask(query, history)