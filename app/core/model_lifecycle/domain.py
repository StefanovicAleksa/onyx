from enum import Enum, auto

class ModelType(Enum):
    """
    Registry of all heavy models that require GPU management.
    Any model listed here MUST be loaded via the ModelLifecycleManager.
    """
    WHISPER = auto()            # Audio -> Text (VRAM: ~500MB - 2GB)
    VISION_QWEN = auto()        # Visual -> Description (VRAM: ~6GB)
    ROUTER_EMBEDDING = auto()   # Text -> Intent (CPU, but managed for RAM safety)
    
    # Future Proofing
    LLAMA_CHAT = auto()         # RAG -> Answer