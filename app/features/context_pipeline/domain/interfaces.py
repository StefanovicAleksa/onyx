# File: app/features/context_pipeline/domain/interfaces.py
from abc import ABC, abstractmethod

class ITokenizer(ABC):
    """
    Abstracts the token counting logic (Tiktoken/HuggingFace)
    so the business logic doesn't depend on a specific library.
    """
    @abstractmethod
    def count_tokens(self, text: str) -> int:
        pass