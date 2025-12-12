import logging
from uuid import UUID
from pathlib import Path
from app.core.database.connection import SessionLocal
from app.core.jobs.models import JobModel, JobStatus
from app.features.storage.data.sql_models import SourceModel
from ..data.sql_models import SourceSpeakerModel
from ..data.nemo_adapter import NemoDiarizationAdapter

logger = logging.getLogger(__name__)

class DiarizationHandler:
    def handle(self, source_id: UUID, params: dict) -> dict:
        logger.info(f"Processing Diarization for Source: {source_id}")
        
        with SessionLocal() as db:
            # 1. Get Audio Path
            source = db.get(SourceModel, source_id)
            if not source: raise ValueError("Source not found")
            audio_path = source.original_file.file_path
            
            # 2. Run Inference
            adapter = NemoDiarizationAdapter()
            result = adapter.identify_speakers(Path(audio_path))
            
            # 3. Save Speakers to DB
            # We want to create unique entries for "speaker_0", "speaker_1" linked to THIS source.
            created_count = 0
            
            # Get unique labels found
            unique_labels = set(s.speaker_label for s in result.segments)
            
            for label in unique_labels:
                # Check if already exists (idempotency)
                exists = db.query(SourceSpeakerModel).filter_by(
                    source_id=source.id,
                    detected_label=label
                ).first()
                
                if not exists:
                    speaker = SourceSpeakerModel(
                        source_id=source.id,
                        detected_label=label,
                        user_label=f"Unknown {label}" # Default name
                    )
                    db.add(speaker)
                    created_count += 1
            
            db.commit()
            
            # 4. (Optional) Update Transcript Segments
            # In a real flow, we would now query the TranscriptionSegment table 
            # and update the 'speaker_id' column based on timestamp overlap.
            # That logic typically lives in an "AlignmentService" which we can build next.

            return {
                "speakers_found": result.num_speakers,
                "new_profiles_created": created_count
            }