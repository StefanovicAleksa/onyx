# File: app/core/database/base.py

from sqlalchemy.orm import declarative_base

# The shared registry. All feature models (Job, File, Transcription) will inherit from this.
Base = declarative_base()