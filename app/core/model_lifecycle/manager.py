import gc
import torch
import logging
from contextlib import contextmanager
from typing import Generator, Any, Callable

logger = logging.getLogger(__name__)

class ModelLifecycleManager:
    """
    Global Resource Governor.
    Ensures only one heavy model occupies the GPU at a time.
    This acts as a 'Mutex' for VRAM.
    """
    
    @staticmethod
    def force_garbage_collection():
        """
        The 'Nuclear Option' for memory cleanup.
        Forces Python and PyTorch to release all unused memory immediately.
        """
        # 1. Force Python's Garbage Collector to release circular references
        gc.collect()
        
        # 2. Empty PyTorch's CUDA cache (the VRAM allocator)
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect() # Helper for clearing shared memory
            
        # Log memory status for debugging (Only if CUDA is active)
        if torch.cuda.is_available():
            free, total = torch.cuda.mem_get_info()
            logger.debug(f"♻️ VRAM Scrubbed. Free: {free/1024**3:.2f}GB / Total: {total/1024**3:.2f}GB")

    @staticmethod
    @contextmanager
    def resource_lock(loader_func: Callable[[], Any], model_name: str) -> Generator[Any, None, None]:
        """
        A Context Manager that handles the safe Setup and Teardown of heavy models.
        
        Args:
            loader_func: A function that returns the loaded model. 
                         (We pass the function, not the result, so we load it INSIDE the lock).
            model_name: String name for logging.
            
        Usage:
            def load_whisper(): return WhisperTranscriber()
            
            with ModelLifecycleManager.resource_lock(load_whisper, "Whisper") as model:
                model.transcribe(...)
            # <-- Model is automatically destroyed and VRAM freed here.
        """
        logger.info(f"🔒 Acquiring GPU Lock for: {model_name}")
        
        # 1. PRE-CLEAN: Ensure the room is empty before we enter
        # This kills any zombie tensors left by previous steps.
        ModelLifecycleManager.force_garbage_collection()
        
        model_instance = None
        try:
            # 2. LOAD: Run the user-provided factory function to get the model
            # This is where VRAM usage spikes.
            model_instance = loader_func()
            yield model_instance
            
        except Exception as e:
            logger.error(f"❌ Error running {model_name}: {e}")
            raise e
            
        finally:
            # 3. TEARDOWN: This block runs even if the code above crashes.
            logger.info(f"🔓 Releasing GPU Lock for: {model_name}")
            
            # Destroy the python object reference explicitly
            if model_instance:
                del model_instance
            
            # 4. POST-CLEAN: Scrub the room for the next person
            ModelLifecycleManager.force_garbage_collection()