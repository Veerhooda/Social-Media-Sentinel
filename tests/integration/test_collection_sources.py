"""Collection sources API and the per-source collection jobs (adapters are faked)."""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings, get_settings
from app.db.repositories.social import SocialRepository
from app.db.session import get_db_session
from app.main import create_app
from app.models.events import AuthorInfo, CanonicalEvent, ContentInfo, RelationshipInfo
from app.platforms.telegram.models import TelegramCheckpoint, TelegramHistoryResult
from app.platforms.youtube.models import YouTubeCheckpoint, YouTubeCommentResult
from app.scheduler.schemas import JobRunStatus
from app.scheduler.service import SchedulerService
from app.sources.jobs import TelegramCollectionJob, YouTubeCollectionJob
from app.sources.repository import SourceRepository
from app.sources.schemas import SourcePlatform, normalise_target

pytestmark = pytest.mark.integration
NOW = datetime(2026, 10, 3, 9, 0, tzinfo=UTC)


def event(platform: str, post_id: str) -> CanonicalEvent:
    return CanonicalEvent(
        platform=platform, platform_post_id=post_id, interaction_type="post" if platform == "telegram" else "comment",
        created_at=NOW, collected_at=NOW + timedelta(seconds=1),
        author=AuthorInfo(platform_user_id=f"a-{post_id}"), content=ContentInfo(text=f"text {post_id}"),
        relationships=RelationshipInfo(), source_metadata={"replay": False},
    )


class FakeTelegram:
    def __init__(self):
        self.calls: list[tuple[str, int | None]] = []
        self.peers: list = []

    async def historical(self, channel, *, max_messages, checkpoint=None, peer=None):
        since = checkpoint.last_message_id if checkpoint else None
        self.calls.append((channel, since))
        self.peers.append((channel, peer))
        if channel == "broken":
            raise RuntimeError("channel is private")
        ids = [101, 102] if since is None else [103]
        return TelegramHistoryResult(
            events=[event("telegram", f"{channel}:{i}") for i in ids],
            checkpoint=TelegramCheckpoint(channel=channel, last_message_id=max(ids)),
            fetched_count=len(ids), rejected_count=0, peer_id=555, peer_access_hash=777,
        )


class FakeYouTube:
    def collect(self, video_id):
        events = [event("youtube", f"{video_id}-c1"), event("youtube", f"{video_id}-c2")]
        return events, YouTubeCommentResult(video_id=video_id, comments_collected=2,
                                            next_checkpoint=YouTubeCheckpoint(video_id=video_id), detail="2 comments")


@pytest.fixture()
def factory(db_engine, db_session):
    return sessionmaker(bind=db_engine, expire_on_commit=False)


def test_target_normalisation():
    assert normalise_target(SourcePlatform.YOUTUBE, "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=1") == "dQw4w9WgXcQ"
    assert normalise_target(SourcePlatform.YOUTUBE, "https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert normalise_target(SourcePlatform.TELEGRAM, "https://t.me/durov") == "durov"
    assert normalise_target(SourcePlatform.TELEGRAM, "@telegram") == "telegram"
    with pytest.raises(ValueError):
        normalise_target(SourcePlatform.YOUTUBE, "not a video")


def test_telegram_job_collects_incrementally_and_isolates_failures(db_session, factory):
    repo = SourceRepository(db_session)
    repo.add(SourcePlatform.TELEGRAM, "news", None)
    repo.add(SourcePlatform.TELEGRAM, "broken", None)
    fake = FakeTelegram()
    settings = Settings(_env_file=None, telegram_api_id=1, telegram_api_hash="h", telegram_session_string="s")
    job = TelegramCollectionJob(settings=settings, session_factory=factory, adapter_factory=lambda _s: fake)

    first = job()
    second = job()

    assert first.status is JobRunStatus.PASS and first.processed_count == 2
    assert second.processed_count == 1
    assert ("news", None) in fake.calls and ("news", 102) in fake.calls
    assert SocialRepository(db_session).count_events() == 3
    db_session.expire_all()
    rows = {r.target: r for r in repo.list(SourcePlatform.TELEGRAM)}
    assert json.loads(rows["news"].cursor) == {"last": 103, "peer": [555, 777]}
    assert rows["news"].total_stored == 3 and rows["news"].last_status == "PASS"
    assert [p for c, p in fake.peers if c == "news"] == [None, (555, 777)]  # cached peer reused: no username resolution
    assert rows["broken"].last_status == "FAIL" and "private" in rows["broken"].last_detail


def test_youtube_job_dedupes_on_repoll(db_session, factory):
    SourceRepository(db_session).add(SourcePlatform.YOUTUBE, "dQw4w9WgXcQ", None)
    job = YouTubeCollectionJob(settings=Settings(_env_file=None, youtube_api_key="k"), session_factory=factory, adapter=FakeYouTube())
    assert job().processed_count == 2
    assert job().processed_count == 0
    assert SocialRepository(db_session).count_events() == 2


def test_jobs_skip_without_credentials_or_sources(factory):
    assert TelegramCollectionJob(settings=Settings(_env_file=None), session_factory=factory)().status is JobRunStatus.SKIPPED
    skipped = YouTubeCollectionJob(settings=Settings(_env_file=None, youtube_api_key="k"), session_factory=factory)()
    assert skipped.status is JobRunStatus.SKIPPED and "Data Sources" in skipped.detail


def test_sources_api_and_manual_run(db_session, factory):
    settings = Settings(_env_file=None, youtube_api_key="k", telegram_channels="seeded_channel")
    scheduler = SchedulerService(enabled=False)
    scheduler.register("youtube_collection", 60, YouTubeCollectionJob(settings=settings, session_factory=factory, adapter=FakeYouTube()))
    app = create_app(scheduler=scheduler, settings=settings)
    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as client:
        overview = client.get("/api/sources").json()
        telegram = next(p for p in overview["platforms"] if p["platform"] == "telegram")
        assert [s["target"] for s in telegram["sources"]] == ["seeded_channel"]
        assert telegram["credentials_configured"] is False

        created = client.post("/api/sources", json={"platform": "youtube", "target": "https://youtu.be/dQw4w9WgXcQ"})
        assert created.status_code == 201 and created.json()["target"] == "dQw4w9WgXcQ"
        assert client.post("/api/sources", json={"platform": "youtube", "target": "nope"}).status_code == 422

        ran = client.post("/api/system/jobs/youtube_collection/run").json()
        assert ran["status"] == "PASS" and ran["processed_count"] == 2
        assert client.post("/api/system/jobs/unknown/run").status_code == 404

        source_id = created.json()["source_id"]
        assert client.patch(f"/api/sources/{source_id}", json={"enabled": False}).json()["enabled"] is False
        assert client.post("/api/system/jobs/youtube_collection/run").json()["status"] == "SKIPPED"
        assert client.delete(f"/api/sources/{source_id}").status_code == 204


def test_demographics_and_audience_sync_jobs_follow_new_accounts(db_session, factory):
    from app.audience_lab.models import AudienceProfile
    from app.db.models import UserDemographic
    from app.sources.jobs import AudienceProfileSyncJob, DemographicsJob

    repo = SocialRepository(db_session)
    for i in range(3):
        repo.insert_event(event("telegram", f"chan:{i}").model_copy(update={
            "author": AuthorInfo(platform_user_id=f"user-{i}", username=f"user{i}", bio="Software engineer in Pune"),
        }))
    repo.commit()
    first = DemographicsJob(session_factory=factory)()
    assert first.status is JobRunStatus.PASS and first.processed_count == 3
    assert DemographicsJob(session_factory=factory)().status is JobRunStatus.SKIPPED
    assert db_session.query(UserDemographic).count() == 3

    synced = AudienceProfileSyncJob(session_factory=factory)()
    assert synced.processed_count == 3 and db_session.query(AudienceProfile).count() == 3
    assert AudienceProfileSyncJob(session_factory=factory)().status is JobRunStatus.SKIPPED
