from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.api.dependencies import get_repository
from app.core.config import Settings
from app.main import create_app
from app.models.events import AuthorInfo, CanonicalEvent, ContentInfo
from app.trends.repository import TrendRepository
from app.trends.schemas import (
    AnalysisStatus,
    BackendAnalysisResult,
    DiscoveredTopic,
    MicroBatch,
)
from app.trends.service import TrendService


class DeterministicTrendAnalyzer:
    engine_name = "BERTrend/test-double"

    def analyze(self, batches: list[MicroBatch]) -> BackendAnalysisResult:
        topics = [
            DiscoveredTopic(
                local_topic_id=0,
                name="open models",
                keywords=["open", "models", "research"],
                document_ids=[document.event_id for document in batch.documents],
                window_start=batch.window_start,
                window_end=batch.window_end,
            )
            for batch in batches
            if batch.documents
        ]
        return BackendAnalysisResult(
            status=AnalysisStatus.PASS,
            engine=self.engine_name,
            topics=topics,
            eligible_batches=len(topics),
            detail="deterministic BERTrend boundary fixture",
        )


def make_event(post_id: str, at: datetime, *, text: str = "Open models research") -> CanonicalEvent:
    return CanonicalEvent(
        platform="x",
        platform_post_id=post_id,
        interaction_type="post",
        created_at=at,
        collected_at=at + timedelta(seconds=2),
        author=AuthorInfo(platform_user_id=f"author-{post_id}"),
        content=ContentInfo(text=text, language="en"),
        source_metadata={"replay": False},
    )


def test_text_extraction_uses_canonical_storage_and_excludes_replay(
    repository, fake_nlp_service
) -> None:
    start = datetime(2026, 9, 20, 10, 0, tzinfo=UTC)
    live = make_event("live", start)
    blank = make_event("blank", start + timedelta(minutes=1), text="   ")
    replay = make_event("replay", start + timedelta(minutes=2))
    replay.source_metadata["replay"] = True
    for event in [live, blank, replay]:
        repository.insert_event(event)
    repository.upsert_nlp_result(live.event_id, fake_nlp_service.analyze(live))

    trend_repository = TrendRepository(repository.session)
    live_documents = trend_repository.list_documents()
    all_documents = trend_repository.list_documents(include_replay=True)

    assert [document.event_id for document in live_documents] == [live.event_id]
    assert live_documents[0].sentiment_label == "positive"
    assert {document.event_id for document in all_documents} == {live.event_id, replay.event_id}


def test_topic_and_measurement_persistence_with_api_serialization(
    repository, fake_nlp_service
) -> None:
    first_window = datetime(2026, 9, 20, 10, 0, tzinfo=UTC)
    events = [
        make_event(f"first-{index}", first_window + timedelta(minutes=index))
        for index in range(3)
    ] + [
        make_event(f"second-{index}", first_window + timedelta(minutes=16 + index))
        for index in range(4)
    ]
    for event in events:
        repository.insert_event(event)
        repository.upsert_nlp_result(event.event_id, fake_nlp_service.analyze(event))

    trend_repository = TrendRepository(repository.session)
    result = TrendService(
        trend_repository,
        analyzer=DeterministicTrendAnalyzer(),
        settings=Settings(trend_window_minutes=15, trend_min_documents=2),
    ).run(platform="x")

    assert result.status is AnalysisStatus.PASS
    assert result.temporal_status is AnalysisStatus.PASS
    assert result.topics_persisted == 1
    assert result.measurements_persisted == 2
    assert trend_repository.count_topics() == 1
    assert trend_repository.count_measurements() == 2
    topic_ids_before = [item.topic_id for item in trend_repository.list_topics()]

    rerun = TrendService(
        trend_repository,
        analyzer=DeterministicTrendAnalyzer(),
        settings=Settings(trend_window_minutes=15, trend_min_documents=2),
    ).run(platform="x")
    assert rerun.status is AnalysisStatus.PASS
    assert trend_repository.count_topics() == 1
    assert trend_repository.count_measurements() == 2
    assert [item.topic_id for item in trend_repository.list_topics()] == topic_ids_before

    topic = trend_repository.list_topics()[0]
    assert topic.volume == 4
    assert topic.growth == 1 / 3
    assert topic.velocity == 4.0
    assert topic.status == "rising"
    assert topic.sentiment == {"positive": 1.0}

    app = create_app()
    app.dependency_overrides[get_repository] = lambda: repository
    with TestClient(app) as client:
        trends = client.get("/api/analytics/trends")
        topics = client.get("/api/analytics/topics")
        detail = client.get(f"/api/analytics/topics/{topic.topic_id}")
        evolution = client.get(f"/api/analytics/topics/{topic.topic_id}/evolution")

    assert trends.status_code == 200
    assert trends.json()["fallback"] is False
    assert trends.json()["items"][0]["sentiment"] == {"positive": 1.0}
    assert topics.status_code == 200
    assert detail.status_code == 200
    assert detail.json()["topic"] == "open models"
    assert evolution.status_code == 200
    assert evolution.json()["status"] == "PASS"
    assert len(evolution.json()["items"]) == 2


def test_empty_database_is_skipped_and_does_not_create_topics(repository) -> None:
    trend_repository = TrendRepository(repository.session)
    result = TrendService(
        trend_repository,
        analyzer=DeterministicTrendAnalyzer(),
        settings=Settings(trend_min_documents=2),
    ).run()

    assert result.status is AnalysisStatus.SKIPPED
    assert result.temporal_status is AnalysisStatus.INSUFFICIENT_DATA
    assert trend_repository.count_topics() == 0
    assert trend_repository.count_measurements() == 0


def test_insufficient_documents_are_not_persisted(repository) -> None:
    event = make_event("only-one", datetime(2026, 9, 20, 10, 0, tzinfo=UTC))
    repository.insert_event(event)
    trend_repository = TrendRepository(repository.session)
    from app.trends.berttrend import BERTrendAnalyzer

    result = TrendService(
        trend_repository,
        analyzer=BERTrendAnalyzer(min_documents=2),
        settings=Settings(trend_min_documents=2),
    ).run()

    assert result.status is AnalysisStatus.INSUFFICIENT_DATA
    assert trend_repository.count_topics() == 0
    assert trend_repository.count_measurements() == 0
