from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.db.models import AnalyticsCheckpoint
from app.db.repositories.social import SocialRepository
from app.db.session import SessionLocal
from app.graph.builder import GraphBuilder
from app.nlp.service import NLPService
from app.scheduler.schemas import JobExecutionResult, JobRunStatus
from app.scheduler.service import SchedulerService
from app.sources.jobs import (  # noqa: F401 - re-exported for existing imports
    AUDIENCE_SYNC_JOB,
    DEMOGRAPHICS_JOB,
    TELEGRAM_COLLECTION_JOB,
    X_COLLECTION_JOB,
    YOUTUBE_COLLECTION_JOB,
    AudienceProfileSyncJob,
    DemographicsJob,
    TelegramCollectionJob,
    XCollectionJob,
    YouTubeCollectionJob,
)
from app.trends.repository import TrendRepository
from app.trends.schemas import AnalysisStatus

NLP_JOB = "nlp_processing"
TREND_JOB = "trend_analysis"
GRAPH_JOB = "graph_refresh"


class JobBatchFailure(RuntimeError):
    def __init__(self, message: str, *, processed_count: int = 0):
        super().__init__(message)
        self.processed_count = processed_count


class CheckpointStore:
    def __init__(self, session: Session):
        self.session = session

    def get(self, job_name: str) -> AnalyticsCheckpoint | None:
        return self.session.get(AnalyticsCheckpoint, job_name)

    def update(
        self,
        job_name: str,
        *,
        cursor_value: str | None = None,
        last_event_collected_at: datetime | None = None,
    ) -> None:
        values = {
            "job_name": job_name,
            "cursor_value": cursor_value,
            "last_event_collected_at": last_event_collected_at,
            "updated_at": datetime.now(UTC),
        }
        statement = insert(AnalyticsCheckpoint).values(**values)
        self.session.execute(
            statement.on_conflict_do_update(
                index_elements=[AnalyticsCheckpoint.job_name],
                set_={key: value for key, value in values.items() if key != "job_name"},
            )
        )
        self.session.commit()


class NLPProcessingJob:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        session_factory: sessionmaker[Session] = SessionLocal,
        nlp_service: NLPService | None = None,
    ):
        self.settings = settings or get_settings()
        self.session_factory = session_factory
        self.nlp_service = nlp_service or NLPService(self.settings)

    def __call__(self) -> JobExecutionResult:
        processed = 0
        failures: list[str] = []
        with self.session_factory() as session:
            repository = SocialRepository(session)
            events = repository.list_events_without_nlp(
                limit=self.settings.analytics_job_batch_size
            )
            for event in events:
                try:
                    result = self.nlp_service.analyze(event)
                    repository.upsert_nlp_result(event.event_id, result)
                    processed += 1
                except Exception as exc:
                    failures.append(f"{event.event_id}: {type(exc).__name__}")
        if failures:
            raise JobBatchFailure(
                f"NLP failed for {len(failures)} event(s): {', '.join(failures[:3])}",
                processed_count=processed,
            )
        return JobExecutionResult(
            status=JobRunStatus.PASS if processed else JobRunStatus.SKIPPED,
            processed_count=processed,
            detail=f"Processed {processed} previously unanalyzed event(s)",
        )


class GraphRefreshJob:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        session_factory: sessionmaker[Session] = SessionLocal,
        graph_builder: GraphBuilder | None = None,
    ):
        self.settings = settings or get_settings()
        self.session_factory = session_factory
        self.graph_builder = graph_builder or GraphBuilder()

    def __call__(self) -> JobExecutionResult:
        processed = 0
        edges_created = 0
        failures: list[str] = []
        with self.session_factory() as session:
            repository = SocialRepository(session)
            events = repository.list_events_without_graph(
                limit=self.settings.analytics_job_batch_size
            )
            for event in events:
                try:
                    edges = self.graph_builder.edges_from_event(event)
                    edges_created += repository.insert_graph_edges(edges)
                    repository.mark_graph_processed(event.event_id, datetime.now(UTC))
                    repository.commit()
                    processed += 1
                except Exception as exc:
                    failures.append(f"{event.event_id}: {type(exc).__name__}")
        if failures:
            raise JobBatchFailure(
                f"Graph processing failed for {len(failures)} event(s): {', '.join(failures[:3])}",
                processed_count=processed,
            )
        return JobExecutionResult(
            status=JobRunStatus.PASS if processed else JobRunStatus.SKIPPED,
            processed_count=processed,
            detail=f"Processed {processed} new event(s); created {edges_created} edge(s)",
        )


class TrendAnalysisJob:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        session_factory: sessionmaker[Session] = SessionLocal,
        trend_service_factory: Any | None = None,
    ):
        self.settings = settings or get_settings()
        self.session_factory = session_factory
        self.trend_service_factory = trend_service_factory

    def __call__(self) -> JobExecutionResult:
        with self.session_factory() as session:
            social_repository = SocialRepository(session)
            trend_repository = TrendRepository(session)
            checkpoints = CheckpointStore(session)
            latest = social_repository.latest_collected_at(
                include_replay=self.settings.analytics_include_replay
            )
            checkpoint = checkpoints.get(TREND_JOB)
            if latest is None:
                return JobExecutionResult(
                    status=JobRunStatus.SKIPPED,
                    detail="No canonical events are available for trend analysis",
                )
            if (
                checkpoint is not None
                and checkpoint.last_event_collected_at is not None
                and checkpoint.last_event_collected_at >= latest
            ):
                return JobExecutionResult(
                    status=JobRunStatus.SKIPPED,
                    detail="No newly collected events since the previous trend run",
                )

            service = (
                self.trend_service_factory(trend_repository)
                if self.trend_service_factory
                else self._default_trend_service(trend_repository)
            )
            result = service.run(include_replay=self.settings.analytics_include_replay)
            if result.status is AnalysisStatus.FAIL:
                raise JobBatchFailure(result.detail or "BERTrend analysis failed")
            checkpoints.update(TREND_JOB, last_event_collected_at=latest)
            operational_status = (
                JobRunStatus.PASS
                if result.status is AnalysisStatus.PASS
                else JobRunStatus.SKIPPED
            )
            return JobExecutionResult(
                status=operational_status,
                processed_count=result.documents,
                detail=(
                    f"{result.status.value}; temporal={result.temporal_status.value}; "
                    f"topics={result.topics_persisted}; measurements={result.measurements_persisted}"
                ),
            )

    def _default_trend_service(self, repository: TrendRepository):
        from app.trends.service import TrendService

        return TrendService(repository, settings=self.settings)


def build_scheduler(
    settings: Settings | None = None,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> SchedulerService:
    settings = settings or get_settings()
    scheduler = SchedulerService(
        enabled=settings.scheduler_enabled,
        tick_seconds=settings.scheduler_tick_seconds,
    )
    scheduler.register(
        X_COLLECTION_JOB,
        settings.x_search_interval_seconds,
        XCollectionJob(settings=settings, session_factory=session_factory),
    )
    scheduler.register(
        TELEGRAM_COLLECTION_JOB,
        settings.telegram_poll_interval_seconds,
        TelegramCollectionJob(settings=settings, session_factory=session_factory),
    )
    scheduler.register(
        YOUTUBE_COLLECTION_JOB,
        settings.youtube_poll_interval_seconds,
        YouTubeCollectionJob(settings=settings, session_factory=session_factory),
    )
    scheduler.register(
        NLP_JOB,
        settings.nlp_processing_interval_seconds,
        NLPProcessingJob(settings=settings, session_factory=session_factory),
    )
    scheduler.register(
        TREND_JOB,
        settings.trend_interval_seconds,
        TrendAnalysisJob(settings=settings, session_factory=session_factory),
    )
    scheduler.register(
        DEMOGRAPHICS_JOB,
        settings.demographics_interval_seconds,
        DemographicsJob(settings=settings, session_factory=session_factory),
    )
    scheduler.register(
        AUDIENCE_SYNC_JOB,
        settings.audience_sync_interval_seconds,
        AudienceProfileSyncJob(settings=settings, session_factory=session_factory),
    )
    scheduler.register(
        GRAPH_JOB,
        settings.graph_interval_seconds,
        GraphRefreshJob(settings=settings, session_factory=session_factory),
    )
    return scheduler
