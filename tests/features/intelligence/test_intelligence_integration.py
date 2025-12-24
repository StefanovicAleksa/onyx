import pytest
import torch
from uuid import uuid4
from app.core.database.connection import SessionLocal, engine
from app.core.database.base import Base
from app.core.common.enums import SourceType, FileType

from app.features.storage.data.sql_models import SourceModel, FileModel
from app.features.context_pipeline.data.sql_models import ContextWindowModel
from app.features.intelligence.data.sql_models import IntelligenceSegmentModel
from app.features.intelligence.data.qwen_adapter import QwenIntelligenceAdapter
from app.features.intelligence.service.job_handler import IntelligenceHandler


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    """Ensure tables exist."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.mark.skipif(not torch.cuda.is_available(), reason="Requires GPU for 7B model test")
def test_intelligence_real_7b_inference():
    """
    ULTIMATE INTEGRATION TEST:
    1. Loads the actual Qwen 2.5 7B Instruct model in 4-bit.
    2. Exercises the real GPU VRAM (approx 5.5GB).
    3. Verifies semantic extraction and DB persistence.
    """
    db = SessionLocal()
    source_id = uuid4()

    # 1. Seed Data (Fixed Flush Order)
    file_rec = FileModel(
        file_path="/tmp/intel_7b_test.txt",
        file_size_bytes=100,
        file_hash="intel_7b_hash",
        file_type=FileType.TEXT
    )
    db.add(file_rec)
    db.flush()  # Fixes the NotNullViolation by generating the ID immediately

    db.add(SourceModel(
        id=source_id,
        name="7B Intelligence Test",
        source_type=SourceType.DOCUMENT,
        file_id=file_rec.id
    ))

    # Complex script to test Qwen's reasoning
    context_text = """
    [00:00:10] Dr. Smith: The patient's blood pressure is 150/90. 
    [00:00:15] Atty. Davis: Is that considered hypertension?
    [00:00:18] Dr. Smith: Yes, Stage 2.
    """
    db.add(ContextWindowModel(
        source_id=source_id,
        window_index=0,
        text_content=context_text,
        token_count=100
    ))
    db.commit()

    # 2. Real 7B Adapter
    # This will use the config we wrote earlier (nf4 quantization)
    adapter = QwenIntelligenceAdapter(model_path="Qwen/Qwen2.5-7B-Instruct")

    print("\n[Test] Loading Qwen 7B into VRAM (This may take a moment)...")
    adapter.load()

    try:
        handler = IntelligenceHandler(adapter=adapter)
        result = handler.handle(source_id)

        # 3. Verify
        assert result["topics_created"] > 0

        saved = db.query(IntelligenceSegmentModel).filter_by(source_id=source_id).first()
        assert saved is not None
        assert "hypertension" in saved.summary.lower()
        print(f"\n[Test] Qwen 7B Result: {saved.title} - {saved.summary}")

    finally:
        adapter.unload()
        db.close()