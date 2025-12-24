import logging
from uuid import UUID
from app.core.database.connection import SessionLocal
from app.features.storage.data.sql_models import SourceModel
from app.features.transcription.data.sql_models import TranscriptionModel, TranscriptionSegmentModel
from ..data.sql_models import SourceSpeakerModel
from ..data.nemo_adapter import NemoDiarizationAdapter

logger = logging.getLogger(__name__)


class DiarizationHandler:
    """
    Worker class responsible for executing DIARIZATION jobs.
    Now performs Speaker-to-Text alignment.
    """

    def handle(self, source_id: UUID, params: dict) -> dict:
        # 'params' is part of the standard interface, even if unused here.
        _ = params

        logger.info(f"Processing Diarization for Source: {source_id}")

        with SessionLocal() as db:
            # 1. Get Audio Path
            source = db.get(SourceModel, source_id)
            if not source:
                raise ValueError("Source not found")

            # Ensure we have the file path
            if not source.original_file:
                raise ValueError(f"Source {source_id} has no file associated")

            # DB stores this as a String, so we use it directly
            audio_path = source.original_file.file_path

            # 2. Run Inference (NeMo)
            # FIX: Pass raw string 'audio_path' instead of 'Path(audio_path)'
            adapter = NemoDiarizationAdapter()
            result = adapter.run_inference(audio_path)

            # 3. Save Speakers to DB & Build a Lookup Map
            # Map: "speaker_0" -> UUID(123-abc...)
            label_to_uuid_map = {}
            created_count = 0

            unique_labels = set(s.speaker_label for s in result.segments)

            for label in unique_labels:
                # Check if already exists
                existing = db.query(SourceSpeakerModel).filter_by(
                    source_id=source.id,
                    detected_label=label
                ).first()

                if not existing:
                    speaker = SourceSpeakerModel(
                        source_id=source.id,
                        detected_label=label,
                        user_label=f"Unknown {label}"
                    )
                    db.add(speaker)
                    db.flush()  # Flush to get the ID
                    label_to_uuid_map[label] = speaker.id
                    created_count += 1
                else:
                    label_to_uuid_map[label] = existing.id

            # 4. Perform Alignment
            # Fetch all text segments for this source
            text_segments = (
                db.query(TranscriptionSegmentModel)
                .join(TranscriptionModel)
                .filter(TranscriptionModel.source_id == source_id)
                .all()
            )

            aligned_count = 0

            if text_segments:
                # Sort diarization segments by start time for efficiency
                diarization_segments = sorted(result.segments, key=lambda x: x.start)

                for txt_seg in text_segments:
                    # Find the speaker segment with the largest overlap
                    midpoint = (txt_seg.start_time + txt_seg.end_time) / 2

                    matched_label = None
                    for ds in diarization_segments:
                        if ds.start <= midpoint <= ds.end:
                            matched_label = ds.speaker_label
                            break

                    if matched_label and matched_label in label_to_uuid_map:
                        txt_seg.speaker_id = label_to_uuid_map[matched_label]
                        aligned_count += 1

            db.commit()

            logger.info(f"Diarization Complete. Created {created_count} profiles. Linked {aligned_count} segments.")

            return {
                "speakers_found": result.num_speakers,
                "new_profiles_created": created_count,
                "segments_aligned": aligned_count
            }