# File: app/core/model_lifecycle/orchestrator.py

import gc
import torch
import logging
from threading import Lock
from .types import ModelType

logger = logging.getLogger(__name__)

class ModelOrchestrator:
    """
    Singleton Resource Manager.
    Ensures only one 'Heavy' AI model is loaded in VRAM at a time.
    """
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ModelOrchestrator, cls).__new__(cls)
                cls._instance._current_type = None
                cls._instance._loaded_model = None
        return cls._instance

    def request_model(self, model_type: ModelType, loader_func):
        """
        Request usage of a model. If it's not loaded, unload current and load requested.
        
        Args:
            model_type: The enum identifier for the model.
            loader_func: A lambda/function that returns the loaded model object.
                         Only called if the model needs to be loaded.
        """
        with self._lock:
            # 1. Already loaded? Return immediately.
            if self._current_type == model_type and self._loaded_model is not None:
                return self._loaded_model

            # 2. Unload different model if exists
            if self._loaded_model is not None:
                self._unload()

            # 3. Load new model
            logger.info(f"Orchestrator: Loading {model_type} into VRAM...")
            try:
                self._loaded_model = loader_func()
                self._current_type = model_type
                return self._loaded_model
            except Exception as e:
                logger.error(f"Failed to load {model_type}: {e}")
                raise e

    def _unload(self):
        """Forcefully removes the current model from VRAM."""
        if self._current_type:
            logger.info(f"Orchestrator: Unloading {self._current_type}...")
        
        # Delete reference
        del self._loaded_model
        self._loaded_model = None
        self._current_type = None
        
        # Force GC and CUDA clear
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            
    def get_current_model_type(self):
        """Helper for testing state."""
        return self._current_type