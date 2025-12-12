# File: app/core/database/connection.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config.settings import settings

# Create the engine. 
# check_same_thread=False is needed only for SQLite (Test Mode)
connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}

engine = create_engine(
    settings.DATABASE_URL, 
    echo=False, 
    pool_pre_ping=True,
    connect_args=connect_args
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Dependency for obtaining a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()