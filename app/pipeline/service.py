from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel

from app.db.repositories.social import SocialRepository
from app.graph.builder import GraphBuilder
from app.models.events import CanonicalEvent
from app.nlp.schemas import NLPResult
from app.nlp.service import NLPService

logger = logging.getLogger(__name__)


class ProcessResult(BaseModel):
    event_id: UUID
    stored: bool
    duplicate: bool
    nlp_processed: bool
    graph_edges_created: int
    nlp: NLPResult | None = None


class EventPipeline:
    def __init__(
        self,
        repository: SocialRepository,
        nlp_service: NLPService,
        graph_builder: GraphBuilder | None = None,
    ):
        self.repository = repository
        self.nlp_service = nlp_service
        self.graph_builder = graph_builder or GraphBuilder()

    def process(self, event: CanonicalEvent, *, stance_target: str | None = None) -> ProcessResult:
        started = time.monotonic()
        write = self.repository.insert_event(event)
        if not write.created:
            return ProcessResult(
                event_id=write.event_id,
                stored=False,
                duplicate=True,
                nlp_processed=False,
                graph_edges_created=0,
            )

        result = self.nlp_service.analyze(event, stance_target=stance_target)
        self.repository.upsert_nlp_result(write.event_id, result)
        edges = self.graph_builder.edges_from_event(event)
        edge_count = self.repository.insert_graph_edges(edges)
        self.repository.mark_graph_processed(write.event_id, datetime.now(UTC))
        self.repository.commit()
        logger.info(
            "Canonical event completed the analytics pipeline",
            extra={
                "service": "event-pipeline",
                "platform": event.platform.value,
                "event_id": str(write.event_id),
                "operation": "process_event",
                "duration_ms": round((time.monotonic() - started) * 1000, 2),
                "status": "PASS",
            },
        )
        return ProcessResult(
            event_id=write.event_id,
            stored=True,
            duplicate=False,
            nlp_processed=True,
            graph_edges_created=edge_count,
            nlp=result,
        )
