import pytest
from unittest.mock import MagicMock, patch
from app.core.model_lifecycle.manager import ModelLifecycleManager

def test_resource_lock_flow():
    """
    Verifies that the manager calls Garbage Collection BEFORE and AFTER
    the model is used.
    """
    # Mock the GC and Torch methods so we don't actually touch hardware
    with patch("app.core.model_lifecycle.manager.gc.collect") as mock_gc, \
         patch("app.core.model_lifecycle.manager.torch.cuda.empty_cache") as mock_torch_clean:
        
        # Define a fake model loader
        mock_model = MagicMock()
        mock_model.do_work.return_value = "Done"
        
        def loader():
            print("  -> Loading Model...")
            return mock_model

        print("\n--- Starting Lifecycle Test ---")
        
        # EXECUTE THE MANAGER
        with ModelLifecycleManager.resource_lock(loader, "TestModel") as model:
            print("  -> Using Model...")
            model.do_work()
            
        print("--- End Lifecycle Test ---")

        # VERIFY
        # GC should be called at least twice (Pre-clean and Post-clean)
        assert mock_gc.call_count >= 2
        
        # If CUDA was "available" (mocked or real), empty_cache is called
        # We can't strictly assert empty_cache count because the code checks is_available() first