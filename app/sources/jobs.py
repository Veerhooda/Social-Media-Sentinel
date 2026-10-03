"""Scheduler jobs that collect from every enabled collection source.

Each job stores canonical events only; the existing NLP, graph and trend jobs
pick new events up on their own schedules (same contract as the X job).
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.db.repositories.social import SocialRepository
from app.db.session import SessionLocal
from app.models.events import CanonicalEvent
from app.scheduler.schemas import JobExecutionResult, JobRunStatus
from app.sources.models import CollectionSource
from app.sources.repository import SourceRepository
from app.sources.schemas import SourcePlatform

log = logging.getLogger(__name__)

X_COLLECTION_JOB = "x_recent_search"
TELEGRAM_COLLECTION_JOB = "telegram_collection"
YOUTUBE_COLLECTION_JOB = "youtube_collection"


def _store(session: Session, events: list[CanonicalEvent]) -> tuple[int, int]:
    repository = SocialRepository(session)
    stored = duplicates = 0
    for event in events:
        write = repository.insert_event(event)
        stored += int(write.created)
        duplicates += int(not write.created)
    return stored, duplicates


class _SourceCollectionJob:
    platform: SourcePlatform
    unconfigured_detail = ""

    def __init__(self, *, settings: Settings | None = None, session_factory: sessionmaker[Session] = SessionLocal):
        self.settings = settings or get_settings()
        self.session_factory = session_factory

    def configured(self) -> bool:  # credentials present
        raise NotImplementedError

    def collect(self, source: CollectionSource) -> tuple[list[CanonicalEvent], str | None, str]:
        """Return (events, new cursor, detail)."""
        raise NotImplementedError

    def __call__(self) -> JobExecutionResult:
        if not self.configured():
            return JobExecutionResult(status=JobRunStatus.SKIPPED, detail=self.unconfigured_detail)
        with self.session_factory() as session:
            sources = SourceRepository(session)
            sources.seed_from_settings(self.settings)
            targets = sources.list(self.platform, enabled_only=True)
            if not targets:
                return JobExecutionResult(
                    status=JobRunStatus.SKIPPED,
                    detail=f"No enabled {self.platform.value} sources. Add one on the Data Sources page.",
                )
            total_stored = total_fetched = 0
            failures: list[str] = []
            for source in targets:
                try:
                    events, cursor, detail = self.collect(source)
                    stored, duplicates = _store(session, events)
                    sources.record_run(
                        source, status="PASS", fetched=len(events), stored=stored, cursor=cursor,
                        detail=f"{detail}; stored {stored}, duplicates {duplicates}",
                    )
                    total_stored += stored
                    total_fetched += len(events)
                except Exception as exc:  # noqa: BLE001 - one bad source must not stop the others
                    session.rollback()
                    message = f"{type(exc).__name__}: {exc}"
                    log.warning("%s source %s failed: %s", self.platform.value, source.target, message)
                    sources.record_run(source, status="FAIL", detail=message)
                    failures.append(f"{source.target}: {message}")
        detail = f"{len(targets)} source(s); fetched {total_fetched}; stored {total_stored}"
        if failures:
            detail += "; failed: " + " | ".join(failures)[:600]
        status = JobRunStatus.FAIL if failures and len(failures) == len(targets) else JobRunStatus.PASS
        return JobExecutionResult(status=status, processed_count=total_stored, detail=detail)


class XCollectionJob(_SourceCollectionJob):
    platform = SourcePlatform.X
    unconfigured_detail = "X credentials (X_BEARER_TOKEN) are not configured"

    def __init__(self, *, settings: Settings | None = None, session_factory: sessionmaker[Session] = SessionLocal, adapter=None):
        super().__init__(settings=settings, session_factory=session_factory)
        self._adapter = adapter

    @property
    def adapter(self):
        if self._adapter is None:
            from app.platforms.x.adapter import XAdapter

            self._adapter = XAdapter(self.settings)
        return self._adapter

    def configured(self) -> bool:
        return bool(self.settings.x_bearer_token)

    def collect(self, source: CollectionSource):
        result = self.adapter.search_recent(
            query=source.target, max_results=self.settings.x_max_results,
            max_pages=self.settings.x_max_pages_per_run, since_id=source.cursor,
        )
        return result.events, result.newest_id or source.cursor, f"fetched {len(result.events)} posts in {result.pages_fetched} page(s)"


class TelegramCollectionJob(_SourceCollectionJob):
    platform = SourcePlatform.TELEGRAM
    unconfigured_detail = "TELEGRAM_API_ID, TELEGRAM_API_HASH and TELEGRAM_SESSION_STRING are not fully configured"

    def __init__(self, *, settings: Settings | None = None, session_factory: sessionmaker[Session] = SessionLocal,
                 adapter_factory: Callable[[Settings], object] | None = None):
        super().__init__(settings=settings, session_factory=session_factory)
        self.adapter_factory = adapter_factory

    def _adapter(self):
        if self.adapter_factory is not None:
            return self.adapter_factory(self.settings)
        from app.platforms.telegram.adapter import TelegramAdapter

        return TelegramAdapter(self.settings)

    def configured(self) -> bool:
        s = self.settings
        return bool(s.telegram_api_id and s.telegram_api_hash and s.telegram_session_string)

    def collect(self, source: CollectionSource):
        from app.platforms.telegram.models import TelegramCheckpoint

        state = _telegram_state(source.cursor)
        checkpoint = (
            TelegramCheckpoint(channel=source.target, last_message_id=state["last"]) if state.get("last") else None
        )
        peer = tuple(state["peer"]) if state.get("peer") else None
        result = asyncio.run(self._adapter().historical(
            source.target, max_messages=self.settings.telegram_max_messages_per_poll,
            checkpoint=checkpoint, peer=peer,
        ))
        if result.checkpoint:
            state["last"] = result.checkpoint.last_message_id
        if result.peer_id and result.peer_access_hash:
            state["peer"] = [result.peer_id, result.peer_access_hash]
        mode = f"new messages since #{checkpoint.last_message_id}" if checkpoint else "latest messages (first run)"
        return result.events, json.dumps(state, separators=(",", ":")), f"fetched {result.fetched_count} {mode}; rejected {result.rejected_count}"


def _telegram_state(cursor: str | None) -> dict:
    """Cursor holds the last message id and the channel's cached peer (id, access hash)."""
    if not cursor:
        return {}
    if cursor.isdigit():  # cursor format used before the peer cache existed
        return {"last": int(cursor)}
    try:
        state = json.loads(cursor)
    except ValueError:
        return {}
    return state if isinstance(state, dict) else {}


class YouTubeCollectionJob(_SourceCollectionJob):
    platform = SourcePlatform.YOUTUBE
    unconfigured_detail = "YOUTUBE_API_KEY is not configured"

    def __init__(self, *, settings: Settings | None = None, session_factory: sessionmaker[Session] = SessionLocal, adapter=None):
        super().__init__(settings=settings, session_factory=session_factory)
        self._adapter = adapter

    @property
    def adapter(self):
        if self._adapter is None:
            from app.platforms.youtube.adapter import YouTubeAdapter

            self._adapter = YouTubeAdapter(self.settings)
        return self._adapter

    def configured(self) -> bool:
        return bool(self.settings.youtube_api_key)

    def collect(self, source: CollectionSource):
        # Comment threads are returned newest-first; re-polling the first pages picks up new
        # comments and the unique (platform, post id) constraint drops ones already stored.
        events, result = self.adapter.collect(source.target)
        return events, None, result.detail or f"fetched {len(events)} comments/replies"


DEMOGRAPHICS_JOB = "demographics_refresh"
AUDIENCE_SYNC_JOB = "audience_profile_sync"


class DemographicsJob:
    """Infer aggregate demographic signals for newly collected accounts (local, keyword backend)."""

    def __init__(self, *, settings: Settings | None = None, session_factory: sessionmaker[Session] = SessionLocal, limit: int = 500):
        self.settings = settings or get_settings()
        self.session_factory = session_factory
        self.limit = limit
        self._service = None

    def _get_service(self):
        if self._service is None:
            from app.demographics.profession import SectorClassifier
            from app.demographics.service import DemographicService

            self._service = DemographicService(sector_classifier=SectorClassifier(backend="keyword", allow_download=False))
        return self._service

    def __call__(self) -> JobExecutionResult:
        from app.demographics.repository import DemographicRepository

        processed = 0
        with self.session_factory() as session:
            repository = DemographicRepository(session)
            missing = repository.list_users_missing_demographics(limit=self.limit)
            if not missing:
                return JobExecutionResult(status=JobRunStatus.SKIPPED, detail="No accounts without demographic signals")
            service = self._get_service()
            for user_id in missing:
                user, texts, languages = repository.collect_user_texts(user_id)
                if user is None:
                    continue
                repository.upsert_signal(service.infer_user(
                    user_id=user_id, platform=user.platform, bio=user.bio, location_raw=user.location_raw,
                    texts=texts, platform_languages=languages,
                ))
                processed += 1
        return JobExecutionResult(status=JobRunStatus.PASS, processed_count=processed,
                                  detail=f"Inferred aggregate signals for {processed} account(s)")


class AudienceProfileSyncJob:
    """Keep Audience Lab profiles in step with collected accounts."""

    def __init__(self, *, settings: Settings | None = None, session_factory: sessionmaker[Session] = SessionLocal):
        self.session_factory = session_factory

    def __call__(self) -> JobExecutionResult:
        from app.audience_lab.profiles import sync_social_profiles

        with self.session_factory() as session:
            result = sync_social_profiles(session)
        changed = result.created + result.updated
        return JobExecutionResult(
            status=JobRunStatus.PASS if result.created else JobRunStatus.SKIPPED,
            processed_count=result.created,
            detail=f"{result.created} new, {result.updated} refreshed; {result.total_profiles} profiles in total" if changed else "No collected accounts",
        )
