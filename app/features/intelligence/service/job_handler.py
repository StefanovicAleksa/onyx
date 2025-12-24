import time
import logging
from uuid import UUID
from typing import Dict, Any, Optional

from app.core.database.connection import SessionLocal
from app.features.context_pipeline.data.sql_models import ContextWindowModel
from ..data.sql_models import IntelligenceSegmentModel
from ..data.qwen_adapter import QwenIntelligenceAdapter
from ..domain.interfaces import ILLMAdapter

logger = logging.getLogger(__name__)


class IntelligenceHandler:
    def __init__(self, adapter: Optional[ILLMAdapter] = None):
        self.adapter = adapter or QwenIntelligenceAdapter()

    def handle(self, source_id: UUID, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        _ = params
        start_time_perf = time.time()
        total_segments = 0

        with SessionLocal() as db:
            windows = (
                db.query(ContextWindowModel)
                .filter(ContextWindowModel.source_id == source_id)
                .order_by(ContextWindowModel.window_index)
                .all()
            )

            if not windows:
                return {"status": "skipped", "reason": "no_windows"}

            for window in windows:
                insights = self.adapter.analyze_text(window.text_content)
                for insight in insights:
                    db_segment = IntelligenceSegmentModel(
                        source_id=source_id,
                        context_window_id=window.id,
                        title=insight.title,
                        summary=insight.summary,
                        keywords=insight.keywords,
                        start_time=insight.start_time,
                        end_time=insight.end_time
                    )
                    db.add(db_segment)
                    total_segments += 1
                db.flush()
            db.commit()

        return {
            "status": "completed",
            "topics_created": total_segments,
            "processing_time": time.time() - start_time_perf
        }