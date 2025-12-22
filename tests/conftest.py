# File: tests/conftest.py

import pytest
import os
import sys
import logging
import sqlalchemy
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import database_exists, create_database

# 1. Add project root to path
sys.path.append(os.getcwd())

# 2. Import Settings
from app.core.config.settings import settings

# 3. Create Test Engine
TEST_ENGINE = create_engine(settings.DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


def silence_nemo():
    """Forces NVIDIA NeMo to stop spamming INFO logs."""
    try:
        from nemo.utils import logging as nemo_logging
        nemo_logging.setLevel(logging.ERROR)
    except ImportError:
        pass


@pytest.fixture(scope="session", autouse=True)
def global_setup():
    """
    Runs once per test session.
    Ensures DB exists and silences logs.
    """
    silence_nemo()

    if not database_exists(TEST_ENGINE.url):
        create_database(TEST_ENGINE.url)

    # Import all models to ensure they are registered
    from app.core.database.base import Base
    import app.core.jobs.models
    import app.features.storage.data.sql_models
    import app.features.transcription.data.sql_models
    import app.features.diarization.data.sql_models
    import app.features.audio_extraction.data.sql_models
    import app.features.video_clipping.data.sql_models

    # Create tables once
    Base.metadata.create_all(bind=TEST_ENGINE)

    yield


@pytest.fixture(scope="function", autouse=True)
def clean_db(global_setup):
    """
    Runs before EVERY test.
    Detects DB type and cleans tables appropriately.
    """
    from app.core.database.base import Base

    # 1. Safety Check: Ensure tables exist
    Base.metadata.create_all(bind=TEST_ENGINE)

    # 2. Clean Data
    with TEST_ENGINE.connect() as conn:
        trans = conn.begin()

        # Check Dialect
        is_sqlite = "sqlite" in str(TEST_ENGINE.url)

        inspector = sqlalchemy.inspect(TEST_ENGINE)
        table_names = inspector.get_table_names()

        if table_names:
            if is_sqlite:
                # SQLite Specific Cleanup (No Truncate, No session_replication_role)
                # We disable foreign key checks temporarily to allow deleting in any order
                conn.execute(text("PRAGMA foreign_keys = OFF;"))
                for table in table_names:
                    conn.execute(text(f'DELETE FROM "{table}";'))
                conn.execute(text("PRAGMA foreign_keys = ON;"))
            else:
                # PostgreSQL Specific Cleanup (Fast Truncate)
                # Disable FK triggers temporarily for speed
                conn.execute(text("SET session_replication_role = 'replica';"))
                for table in table_names:
                    conn.execute(text(f'TRUNCATE TABLE "{table}" CASCADE;'))
                conn.execute(text("SET session_replication_role = 'origin';"))

        trans.commit()

    yield


@pytest.fixture(scope="function")
def db_session():
    """
    Provides a session for the test to use.
    """
    connection = TEST_ENGINE.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()