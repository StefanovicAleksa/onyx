import pytest
from uuid import uuid4
from typing import List
from app.core.database.connection import SessionLocal, engine
from app.core.database.base import Base
from app.core.common.enums import SourceType, FileType

from app.features.storage.data.sql_models import SourceModel, FileModel
from app.features.context_pipeline.data.sql_models import ContextWindowModel
from app.features.intelligence.data.sql_models import IntelligenceSegmentModel
from app.features.intelligence.domain.models import IntelligenceInsight
from app.features.intelligence.domain.interfaces import ILLMAdapter
from app.features.intelligence.service.job_handler import IntelligenceHandler


class MockQwenAdapter(ILLMAdapter):
    def load(self): pass

    def unload(self): pass

    def analyze_text(self, text: str) -> List[IntelligenceInsight]:
        # Return a deterministic insight
        return [IntelligenceInsight(
            title="Liability Argument",
            summary="Discussion of fault.",
            start_time=10.0,
            end_time=20.0,
            keywords=["liability"]
        )]


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_intelligence_integration_db_save():
    """Verifies that the handler correctly saves data to the DB."""
    db = SessionLocal()
    source_id = uuid4()

    # 1. Seed
    file_rec = FileModel(file_path="/tmp/i.txt", file_size_bytes=10,
                         file_hash="h1", file_type=FileType.TEXT)
    db.add(file_rec)
    db.add(SourceModel(id=source_id, name="Test", source_type=SourceType.DOCUMENT, file_id=file_rec.id))
    db.add(ContextWindowModel(source_id=source_id, window_index=0, text_content="Data", token_count=1))
    db.commit()

    # 2. Execute
    handler = IntelligenceHandler(adapter=MockQwenAdapter())
    handler.handle(source_id)

    # 3. Verify (Using the previously 'unused' import)
    saved = db.query(IntelligenceSegmentModel).filter_by(source_id=source_id).first()
    assert saved is not None
    assert saved.title == "Liability Argument"
    assert "liability" in saved.keywords

    db.close()