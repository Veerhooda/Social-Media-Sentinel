from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.db.repositories.social import SocialRepository
from app.models.events import AuthorInfo, CanonicalEvent, ContentInfo, RelationshipInfo
from app.platforms.x.models import XSearchResult
from app.scheduler.jobs import (
    GraphRefreshJob,
    JobBatchFailure,
    NLPProcessingJob,
    TrendAnalysisJob,
    XCollectionJob,
)
from app.scheduler.schemas import JobRunStatus
from app.trends.schemas import (
    AnalysisStatus,
    BackendAnalysisResult,
    DiscoveredTopic,
    MicroBatch,
)
from app.trends.service import TrendService


def make_event(
    post_id: str,
    at: datetime,
    *,
    replay: bool = False,
    mention: bool = False,
) -> CanonicalEvent:
    return CanonicalEvent(
        platform="x",
        platform_post_id=post_id,
        interaction_type="mention" if mention else "post",
        created_at=at,
        collected_at=at + timedelta(seconds=2),
        author=AuthorInfo(platform_user_id=f"author-{post_id}"),
        content=ContentInfo(
            text=f"Scheduled analytics event {post_id}",
            language="en",
            mentions=["target"] if mention else [],
        ),
        relationships=RelationshipInfo(),
        source_metadata={
            "replay": replay,
            "mention_ids": ["target-id"] if mention else [],
        },
    )


class FakeXAdapter:
    def __init__(self, events: list[CanonicalEvent]):
        self.events = events
        self.since_ids: list[str | None] = []

    def search_recent(self, **kwargs) -> XSearchResult:
        self.since_ids.append(kwargs.get("since_id"))
        return XSearchResult(
            events=self.events,
            pages_fetched=1,
            newest_id="cursor-2",
            oldest_id="cursor-1",
        )


class DeterministicScheduledTrendAnalyzer:
    engine_name = "BERTrend/scheduler-test"

    def analyze(self, batches: list[MicroBatch]) -> BackendAnalysisResult:
        topics = [
            DiscoveredTopic(
                local_topic_id=0,
                name="scheduled analytics",
                keywords=["scheduled", "analytics"],
                document_ids=[document.event_id for document in batch.documents],
                window_start=batch.window_start,
                window_end=batch.window_end,
                lineage_key="scheduled-analytics",
            )
            for batch in batches
            if batch.documents
        ]
        return BackendAnalysisResult(
            status=AnalysisStatus.PASS,
            engine=self.engine_name,
            topics=topics,
            eligible_batches=len(topics),
        )


def factory(db_engine) -> sessionmaker[Session]:
    return sessionmaker(bind=db_engine, expire_on_commit=False)


def test_x_collection_stores_only_new_events_and_persists_cursor(db_session, db_engine) -> None:
    event = make_event("x-job", datetime(2026, 9, 20, 10, 0, tzinfo=UTC))
    adapter = FakeXAdapter([event])
    settings = Settings(x_bearer_token="fixture", x_query="fixture query")
    job = XCollectionJob(
        settings=settings,
        session_factory=factory(db_engine),
        adapter=adapter,  # type: ignore[arg-type]
    )

    first = job()
    second = job()

    assert first.status is JobRunStatus.PASS
    assert first.processed_count == 1
    assert second.processed_count == 0
    assert adapter.since_ids == [None, "cursor-2"]
    assert SocialRepository(db_session).count_events() == 1


def test_nlp_job_processes_only_newly_arrived_events(
    db_session, db_engine, fake_nlp_service
) -> None:
    repository = SocialRepository(db_session)
    start = datetime(2026, 9, 20, 10, 0, tzinfo=UTC)
    repository.insert_event(make_event("nlp-one", start))
    job = NLPProcessingJob(
        settings=Settings(analytics_job_batch_size=10),
        session_factory=factory(db_engine),
        nlp_service=fake_nlp_service,
    )

    assert job().processed_count == 1
    assert job().status is JobRunStatus.SKIPPED
    repository.insert_event(make_event("nlp-two", start + timedelta(minutes=1)))
    assert job().processed_count == 1
    assert repository.list_events_without_nlp() == []


def test_nlp_failure_preserves_stored_event(db_session, db_engine) -> None:
    repository = SocialRepository(db_session)
    repository.insert_event(
        make_event("nlp-failure", datetime(2026, 9, 20, 10, 0, tzinfo=UTC))
    )

    class FailingNLP:
        def analyze(self, event):
            raise RuntimeError("controlled model failure")

    job = NLPProcessingJob(
        settings=Settings(analytics_job_batch_size=10),
        session_factory=factory(db_engine),
        nlp_service=FailingNLP(),  # type: ignore[arg-type]
    )

    with pytest.raises(JobBatchFailure, match="NLP failed"):
        job()
    assert repository.count_events() == 1
    assert len(repository.list_events_without_nlp()) == 1


def test_graph_job_processes_each_event_once(db_session, db_engine) -> None:
    repository = SocialRepository(db_session)
    repository.insert_event(
        make_event("graph-one", datetime(2026, 9, 20, 10, 0, tzinfo=UTC), mention=True)
    )
    job = GraphRefreshJob(
        settings=Settings(analytics_job_batch_size=10),
        session_factory=factory(db_engine),
    )

    first = job()
    second = job()

    assert first.processed_count == 1
    assert "created 1 edge" in first.detail
    assert second.status is JobRunStatus.SKIPPED
    assert len(repository.list_graph_edges()) == 1
    assert repository.list_events_without_graph() == []


def test_trend_job_refreshes_only_when_new_events_arrive(db_session, db_engine) -> None:
    repository = SocialRepository(db_session)
    start = datetime(2026, 9, 20, 10, 0, tzinfo=UTC)
    repository.insert_event(make_event("trend-one", start))
    repository.insert_event(make_event("trend-two", start + timedelta(minutes=1)))
    settings = Settings(trend_min_documents=2, analytics_job_batch_size=10)
    job = TrendAnalysisJob(
        settings=settings,
        session_factory=factory(db_engine),
        trend_service_factory=lambda trend_repository: TrendService(
            trend_repository,
            analyzer=DeterministicScheduledTrendAnalyzer(),
            settings=settings,
        ),
    )

    first = job()
    second = job()

    assert first.status is JobRunStatus.PASS
    assert first.processed_count == 2
    assert second.status is JobRunStatus.SKIPPED
    assert "No newly collected events" in second.detail


def test_replay_uses_same_scheduled_analytics_jobs(
    db_session, db_engine, fake_nlp_service
) -> None:
    repository = SocialRepository(db_session)
    start = datetime(2026, 9, 20, 10, 0, tzinfo=UTC)
    repository.insert_event(make_event("replay-one", start, replay=True, mention=True))
    repository.insert_event(
        make_event("replay-two", start + timedelta(minutes=1), replay=True)
    )
    settings = Settings(
        analytics_include_replay=True,
        analytics_job_batch_size=10,
        trend_min_documents=2,
    )

    nlp = NLPProcessingJob(
        settings=settings,
        session_factory=factory(db_engine),
        nlp_service=fake_nlp_service,
    )()
    graph = GraphRefreshJob(
        settings=settings,
        session_factory=factory(db_engine),
    )()
    trend = TrendAnalysisJob(
        settings=settings,
        session_factory=factory(db_engine),
        trend_service_factory=lambda trend_repository: TrendService(
            trend_repository,
            analyzer=DeterministicScheduledTrendAnalyzer(),
            settings=settings,
        ),
    )()

    assert nlp.processed_count == 2
    assert graph.processed_count == 2
    assert trend.status is JobRunStatus.PASS
    assert trend.processed_count == 2
