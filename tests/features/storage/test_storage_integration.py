import pytest
from pathlib import Path
from app.core.database.base import Base
from app.core.database.connection import engine, SessionLocal
from app.core.common.enums import SourceType
from app.features.storage.service.api import storage
from app.features.storage.domain.models import IngestRequest
from app.features.storage.data.sql_models import FileModel, SourceModel

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_ingest_and_deduplication(tmp_path):
    """
    Scenario:
    1. User uploads 'contract.pdf'.
    2. User uploads 'contract_copy.pdf' (Same content).
    3. System should create 2 Sources but only 1 Physical File.
    """
    # Setup
    content = b"This is a unique contract content."
    
    file1 = tmp_path / "contract.txt"
    file1.write_bytes(content)
    
    file2 = tmp_path / "contract_copy.txt"
    file2.write_bytes(content) # Identical content
    
    # 1. Ingest First File
    req1 = IngestRequest(file1, "Contract V1", SourceType.DOCUMENT)
    source_id_1 = storage.ingest_file(req1)
    
    # 2. Ingest Second File
    req2 = IngestRequest(file2, "Contract Copy", SourceType.DOCUMENT)
    source_id_2 = storage.ingest_file(req2)
    
    # 3. Verification
    assert source_id_1 != source_id_2, "Sources should be unique entities"
    
    with SessionLocal() as db:
        # Check Sources
        s1 = db.get(SourceModel, source_id_1)
        s2 = db.get(SourceModel, source_id_2)
        
        assert s1.name == "Contract V1"
        assert s2.name == "Contract Copy"
        
        # KEY CHECK: They should point to the SAME File ID
        assert s1.file_id == s2.file_id
        
        # Check Files Table
        file_count = db.query(FileModel).count()
        assert file_count == 1, "Should only be 1 physical file record"
        
        stored_file = db.get(FileModel, s1.file_id)
        assert Path(stored_file.file_path).exists(), "Physical file should exist in artifacts"