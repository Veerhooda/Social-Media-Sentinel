from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_repository
from app.main import create_app
from app.models.events import AuthorInfo, CanonicalEvent, ContentInfo
from app.pipeline.service import EventPipeline
from app.platforms.telegram.adapter import TelegramAdapter
from app.platforms.telegram.client import TelegramClient
from app.platforms.telegram.mapper import TelegramEventMapper
from app.trends.repository import TrendRepository
from app.trends.schemas import (
    AnalysisStatus,
    BackendAnalysisResult,
    DiscoveredTopic,
    MicroBatch,
)
from app.trends.service import TrendService


class TelegramTrendAnalyzer:
    engine_name = "BERTrend/telegram-boundary-test"

    def analyze(self, batches: list[MicroBatch]) -> BackendAnalysisResult:
        assert all(
            document.platform == "telegram"
            for batch in batches
            for document in batch.documents
        )
        topics = [
            DiscoveredTopic(
                local_topic_id=0,
                name="telegram public research",
                keywords=["telegram", "research"],
                document_ids=[document.event_id for document in batch.documents],
                window_start=batch.window_start,
                window_end=batch.window_end,
                lineage_key="telegram-public-research",
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


def telegram_reply() -> CanonicalEvent:
    chat = SimpleNamespace(
        id=777,
        title="Public Research",
        username="public_research",
        broadcast=True,
        megagroup=False,
    )
    parent_sender = SimpleNamespace(
        id=2002,
        username="parent_author",
        first_name="Parent",
        last_name="Author",
        verified=False,
    )
    parent = SimpleNamespace(id=70, sender_id=2002, sender=parent_sender)
    author = SimpleNamespace(
        id=1001,
        username="telegram_author",
        first_name="Telegram",
        last_name="Author",
        verified=False,
    )
    message = SimpleNamespace(
        id=71,
        chat_id=-100777,
        sender_id=1001,
        sender=author,
        date=datetime(2026, 9, 20, 10, 2, tzinfo=UTC),
        raw_text="Public Telegram research reply #OpenData @peer",
        reply_to_msg_id=70,
        reply_to=SimpleNamespace(reply_to_msg_id=70, reply_to_top_id=70),
        fwd_from=None,
        entities=[],
        media=None,
        forwards=2,
        views=30,
        replies=SimpleNamespace(replies=1),
        reactions=SimpleNamespace(results=[SimpleNamespace(count=4)]),
        post_author=None,
    )
    return TelegramEventMapper().map_message(
        message,
        sender=author,
        chat=chat,
        reply_message=parent,
        reply_sender=parent_sender,
        collected_at=datetime(2026, 9, 20, 10, 2, 5, tzinfo=UTC),
    )


class FakeHistoryClient:
    def __init__(self):
        self.chat = SimpleNamespace(
            id=888,
            title="Public History",
            username="public_history",
            broadcast=True,
            megagroup=False,
        )
        author = SimpleNamespace(
            id=3003,
            username="history_author",
            first_name="History",
            last_name="Author",
            verified=False,
        )
        self.message = SimpleNamespace(
            id=80,
            chat_id=-100888,
            sender_id=3003,
            sender=author,
            date=datetime(2026, 9, 20, 10, 4, tzinfo=UTC),
            raw_text="Adapter history into the canonical pipeline",
            reply_to_msg_id=None,
            reply_to=None,
            fwd_from=None,
            entities=[],
            media=None,
            forwards=0,
            views=10,
            replies=None,
            reactions=None,
            post_author=None,
        )

    async def connect(self):
        return None

    async def is_user_authorized(self):
        return True

    async def disconnect(self):
        return None

    async def get_entity(self, target):
        return self.chat

    def iter_messages(self, entity, *, limit, offset_date, min_id, reverse):
        async def iterator():
            if self.message.id > min_id:
                yield self.message

        return iterator()

    async def get_messages(self, entity, *, ids):
        return []


@pytest.mark.asyncio
async def test_mocked_history_adapter_to_canonical_postgres_and_deduplication(
    repository, fake_nlp_service
) -> None:
    adapter = TelegramAdapter(
        telegram_client=TelegramClient(client=FakeHistoryClient())
    )
    history = await adapter.historical("public_history", max_messages=1)
    pipeline = EventPipeline(repository, fake_nlp_service)

    first = pipeline.process(history.events[0])
    second = pipeline.process(history.events[0])

    assert history.fetched_count == 1
    assert first.stored is True
    assert second.duplicate is True
    assert (
        repository.list_events(platform="telegram")[0].platform_post_id == "-100888:80"
    )


def test_telegram_to_shared_postgres_nlp_temporal_trend_graph_and_api(
    repository, fake_nlp_service
) -> None:
    telegram = telegram_reply()
    pipeline = EventPipeline(repository, fake_nlp_service)
    first = pipeline.process(telegram)
    duplicate = pipeline.process(telegram)

    existing_x = CanonicalEvent(
        platform="x",
        platform_post_id="existing-x-fixture",
        interaction_type="post",
        created_at=telegram.created_at - timedelta(minutes=1),
        collected_at=telegram.collected_at - timedelta(minutes=1),
        author=AuthorInfo(platform_user_id="existing-x-author"),
        content=ContentInfo(text="Existing stored X fixture for coexistence"),
        source_metadata={"replay": False},
    )
    pipeline.process(existing_x)

    trend_settings = (
        pipeline.nlp_service
    )  # prove no Telegram-specific NLP service is introduced
    assert trend_settings is fake_nlp_service
    trend_result = TrendService(
        TrendRepository(repository.session),
        analyzer=TelegramTrendAnalyzer(),
    ).run(platform="telegram")

    assert first.stored is True
    assert first.nlp_processed is True
    assert first.graph_edges_created == 2
    assert duplicate.duplicate is True
    assert duplicate.nlp_processed is False
    assert trend_result.status is AnalysisStatus.PASS
    assert trend_result.temporal_status is AnalysisStatus.INSUFFICIENT_DATA
    assert trend_result.documents == 1
    assert trend_result.topics_persisted == 1

    ordered = repository.list_events()
    assert [event.platform.value for event in ordered] == ["x", "telegram"]
    assert repository.count_events(platform="telegram") == 1
    stored = repository.list_events(platform="telegram")[0]
    assert stored.created_at == telegram.created_at
    assert stored.collected_at == telegram.collected_at

    app = create_app()
    app.dependency_overrides[get_repository] = lambda: repository
    with TestClient(app) as client:
        health = client.get("/api/health")
        telegram_events = client.get("/api/events", params={"platform": "telegram"})
        live = client.get("/api/events/live", params={"platform": "telegram"})
        sentiment = client.get(
            "/api/analytics/sentiment", params={"platform": "telegram"}
        )
        emotions = client.get(
            "/api/analytics/emotions", params={"platform": "telegram"}
        )
        trends = client.get("/api/analytics/trends")
        network = client.get("/api/network/summary", params={"platform": "telegram"})

    assert health.status_code == 200
    assert health.json()["database"]["status"] == "PASS"
    assert health.json()["telegram_api"]["status"] in {"PASS", "SKIPPED"}
    assert telegram_events.status_code == 200
    assert telegram_events.json()["total"] == 1
    assert telegram_events.json()["items"][0]["platform_post_id"] == "-100777:71"
    assert live.json()["mode"] == "live"
    assert sentiment.json()["rolling_1h"][0]["positive_ratio"] == 1.0
    assert emotions.json()["rolling_1h"][0]["anxiety_average"] == 0.2
    assert trends.json()["engine"] == "BERTrend/telegram-boundary-test"
    assert network.json()["summary"]["nodes"] == 3
    assert network.json()["summary"]["edges"] == 2
