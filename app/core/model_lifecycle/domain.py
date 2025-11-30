from enum import Enum, auto

class ModelType(Enum):
    """
    Registry of all heavy models that require Lifecycle Management.
    """
    WHISPER = auto()            # Audio -> Text (VRAM: ~500MB - 2GB)
    VISION_QWEN = auto()        # Visual -> Description (VRAM: ~2GB - 6GB)
    ROUTER_EMBEDDING = auto()   # Text -> Intent (CPU, but managed for RAM safety)
    
    # --- RAG Components ---
    EMBEDDING_MODEL = auto()    # The Librarian: Text -> Vector (CPU: ~150MB RAM)
    LLAMA_CHAT = auto()         # The Expert: RAG -> Answer (VRAM: ~6GB for Llama3, ~2GB for Qwen)