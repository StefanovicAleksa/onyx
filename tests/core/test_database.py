# File: tests/integration/core/test_database.py

import pytest
from sqlalchemy import text
from app.core.database.connection import get_db

def test_database_connection():
    """
    Simple smoke test to ensure DB is reachable and configured.
    """
    db_gen = get_db()
    db = next(db_gen)
    try:
        # Simple query valid in both Postgres and SQLite
        result = db.execute(text("SELECT 1"))
        assert result.scalar() == 1
    finally:
        db.close()