from abc import ABC, abstractmethod
from typing import List
from .models import KnowledgeChunk, SearchResult

class IEmbedder(ABC):
    """
    Interface for converting text to vector representations.
    """
    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embeds a list of documents/passages.
        For BGE-v1.5, this typically does NOT require an instruction prefix.
        """
        pass

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """
        Embeds a single user query.
        For BGE-v1.5, this REQUIRES an instruction prefix.
        """
        pass

class IVectorStore(ABC):
    """
    Interface for the Vector Database (CRUD operations).
    """
    @abstractmethod
    def upsert(self, chunks: List[KnowledgeChunk], vectors: List[List[float]]) -> None:
        """
        Inserts or updates chunks in the database.
        """
        pass

    @abstractmethod
    def search(self, query_vector: List[float], limit: int = 5) -> List[SearchResult]:
        """
        Finds the nearest neighbors to the query vector.
        """
        pass