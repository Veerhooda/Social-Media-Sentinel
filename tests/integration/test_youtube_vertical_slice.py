"""Local YouTube response through canonical persistence and shared analytics."""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.analytics.temporal import aggregate_rolling
from app.api.dependencies import get_repository
from app.core.config import Settings
from app.main import create_app
from app.models.events import AuthorInfo, CanonicalEvent, ContentInfo, Platform
from app.pipeline.service import EventPipeline
from app.platforms.youtube.adapter import YouTubeAdapter
from app.platforms.youtube.client import YouTubeClient
from app.trends.repository import TrendRepository
from app.trends.schemas import AnalysisStatus, BackendAnalysisResult, MicroBatch
from app.trends.service import TrendService

FIXTURES = Path(__file__).parent.parent / "fixtures"
THREADS = json.loads((FIXTURES / "youtube_thread_response.json").read_text())
REPLIES = json.loads((FIXTURES / "youtube_comments_response.json").read_text())


class FixtureResource:
    def __init__(self):
        self.kind = ""

    def commentThreads(self):  # noqa: N802
        self.kind = "threads"
        return self

    def comments(self):
        self.kind = "replies"
        return self

    def list(self, **kwargs):
        return self

    def execute(self):
        return THREADS if self.kind == "threads" else REPLIES


class InsufficientAnalyzer:
    engine_name = "BERTrend/fixture-boundary"

    def analyze(self, batches: list[MicroBatch]) -> BackendAnalysisResult:
        assert all(document.platform == "youtube" for batch in batches for document in batch.documents)
        return BackendAnalysisResult(
            status=AnalysisStatus.INSUFFICIENT_DATA,
            engine=self.engine_name,
            eligible_batches=0,
            detail="Too few YouTube documents for topic discovery",
        )


def test_youtube_response_to_shared_pipeline_and_api(repository, fake_nlp_service) -> None:
    adapter = YouTubeAdapter(
        settings=Settings(youtube_api_key="fixture"),
        youtube_client=YouTubeClient(service=FixtureResource()),
    )
    events, retrieval = adapter.collect("video-abc", max_pages=1, max_results=10)
    assert retrieval.replies_collected == 2
    assert len(events) == 4
    by_id = {event.platform_post_id: event for event in events}
    assert by_id["comment-reply-1"].relationships.parent_author_id == "UC_top1"
    assert by_id["comment-top-1"].created_at == datetime(2026, 9, 18, 10, tzinfo=UTC)
    assert by_id["comment-top-1"].collected_at > by_id["comment-top-1"].created_at

    existing_x = CanonicalEvent(
        platform="x", platform_post_id="fixture-x", interaction_type="post",
        created_at=events[0].created_at - timedelta(minutes=1),
        author=AuthorInfo(platform_user_id="fixture-x-author"),
        content=ContentInfo(text="Existing X fixture"),
        source_metadata={"replay": True},
    )
    existing_telegram = existing_x.model_copy(
        update={
            "platform": Platform.TELEGRAM, "platform_post_id": "fixture-telegram",
            "event_id": uuid4(),
        }
    )
    pipeline = EventPipeline(repository, fake_nlp_service)
    for event in [existing_x, existing_telegram, *events]:
        assert pipeline.process(event).stored
    duplicate = pipeline.process(events[0])
    assert duplicate.duplicate and not duplicate.nlp_processed
    assert repository.count_events(platform="youtube") == 4
    assert len(repository.list_graph_edges(platform="youtube")) == 2
    assert {event.platform.value for event in repository.list_events(limit=10)} == {"x", "telegram", "youtube"}
    assert aggregate_rolling(repository.list_nlp_results(platform="youtube"))

    trend = TrendService(
        TrendRepository(repository.session),
        analyzer=InsufficientAnalyzer(),
        settings=Settings(trend_min_documents=10),
    ).run(platform="youtube")
    assert trend.status is AnalysisStatus.INSUFFICIENT_DATA
    assert trend.topics_persisted == 0

    app = create_app()
    app.dependency_overrides[get_repository] = lambda: repository
    with TestClient(app) as client:
        event_response = client.get("/api/events", params={"platform": "youtube"})
        enriched = client.get("/api/events/enriched", params={"platform": "youtube"})
        sentiment = client.get("/api/analytics/sentiment", params={"platform": "youtube"})
        graph = client.get("/api/network/graph", params={"platform": "youtube"})
    assert event_response.status_code == 200 and event_response.json()["total"] == 4
    assert enriched.status_code == 200
    assert all(item["analysis"]["sentiment"]["label"] == "positive" for item in enriched.json()["items"])
    assert sentiment.status_code == 200 and sentiment.json()["rolling_1h"]
    assert graph.status_code == 200 and graph.json()["edge_count"] == 2
    assert all(edge["interaction_type"] == "reply" for edge in graph.json()["edges"])
