from abc import ABC, abstractmethod
from typing import List
from .models import ChatRequest, ChatResponse
from app.features.knowledge_base.domain.models import SearchResult

class IChatModel(ABC):
    @abstractmethod
    def generate_response(self, request: ChatRequest, context_chunks: List[SearchResult]) -> ChatResponse:
        """
        Generates an answer based on the provided Context Chunks (RAG).
        """
        pass