from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.sources.models import CollectionSource
from app.sources.schemas import SourcePlatform, normalise_target


class SourceRepository:
    def __init__(self, session: Session):
        self.session = session

    def seed_from_settings(self, settings: Settings) -> None:
        """Make .env-configured targets visible/editable as rows (idempotent, never re-enables)."""
        seeds: list[tuple[SourcePlatform, str]] = []
        if settings.x_query.strip():
            seeds.append((SourcePlatform.X, settings.x_query.strip()))
        for channel in settings.telegram_channel_list:
            seeds.append((SourcePlatform.TELEGRAM, channel))
        for video in settings.youtube_video_list:
            seeds.append((SourcePlatform.YOUTUBE, video))
        for platform, raw in seeds:
            try:
                target = normalise_target(platform, raw)
            except ValueError:
                continue
            self.session.execute(
                insert(CollectionSource)
                .values(platform=platform.value, target=target, label="from .env", enabled=True)
                .on_conflict_do_nothing(constraint="uq_collection_source_target")
            )
        self.session.commit()

    def list(self, platform: SourcePlatform | None = None, *, enabled_only: bool = False) -> list[CollectionSource]:
        query = select(CollectionSource).order_by(CollectionSource.platform, CollectionSource.created_at)
        if platform is not None:
            query = query.where(CollectionSource.platform == platform.value)
        if enabled_only:
            query = query.where(CollectionSource.enabled.is_(True))
        return list(self.session.scalars(query))

    def get(self, source_id: UUID) -> CollectionSource | None:
        return self.session.get(CollectionSource, source_id)

    def add(self, platform: SourcePlatform, target: str, label: str | None) -> CollectionSource:
        existing = self.session.scalar(
            select(CollectionSource).where(CollectionSource.platform == platform.value, CollectionSource.target == target)
        )
        if existing is not None:
            existing.enabled = True
            if label:
                existing.label = label
            self.session.commit()
            return existing
        row = CollectionSource(platform=platform.value, target=target, label=label, enabled=True)
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def delete(self, row: CollectionSource) -> None:
        self.session.delete(row)
        self.session.commit()

    def record_run(
        self, row: CollectionSource, *, status: str, detail: str,
        fetched: int = 0, stored: int = 0, cursor: str | None = None,
    ) -> None:
        row.last_run_at = datetime.now(UTC)
        row.last_status = status
        row.last_detail = detail[:2000]
        row.last_fetched = fetched
        row.last_stored = stored
        row.total_stored += stored
        if cursor is not None:
            row.cursor = cursor
        self.session.commit()
