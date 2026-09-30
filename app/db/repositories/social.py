from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, func, or_, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.models import (
    DeadLetterEvent,
    GraphEdge,
    NLPAnalysis,
    SocialEvent,
    SocialUser,
)
from app.graph.schemas import EdgeRecord
from app.models.events import (
    AuthorInfo,
    CanonicalEvent,
    ContentInfo,
    EngagementMetrics,
    MediaInfo,
    RelationshipInfo,
)
from app.nlp.schemas import NLPResult


@dataclass(frozen=True)
class EventWriteResult:
    event_id: UUID
    created: bool


class SocialRepository:
    def __init__(self, session: Session):
        self.session = session

    def health_check(self) -> bool:
        return self.session.execute(text("SELECT 1")).scalar_one() == 1

    def upsert_user(self, event: CanonicalEvent) -> UUID:
        author = event.author
        values = {
            "platform": event.platform.value,
            "platform_user_id": author.platform_user_id,
            "username": author.username,
            "display_name": author.display_name,
            "bio": author.bio,
            "location_raw": author.location_raw,
            "avatar_url": str(author.avatar_url) if author.avatar_url else None,
            "followers_count": author.followers_count,
            "following_count": author.following_count,
            "is_verified": author.is_verified,
        }
        statement = insert(SocialUser).values(**values)
        statement = statement.on_conflict_do_update(
            constraint="uq_user_platform_id",
            set_={**values, "last_seen_at": func.now()},
        ).returning(SocialUser.user_id)
        return self.session.execute(statement).scalar_one()

    def insert_event(self, event: CanonicalEvent) -> EventWriteResult:
        author_id = self.upsert_user(event)
        payload = event.model_dump(mode="json")
        statement = (
            insert(SocialEvent)
            .values(
                event_id=event.event_id,
                platform=event.platform.value,
                platform_post_id=event.platform_post_id,
                parent_platform_post_id=event.parent_platform_post_id,
                thread_root_id=event.thread_root_id,
                author_id=author_id,
                interaction_type=event.interaction_type.value,
                created_at=event.created_at,
                collected_at=event.collected_at,
                content_text=event.content.text,
                language_code=event.content.language,
                hashtags=event.content.hashtags,
                mentions=event.content.mentions,
                media=payload["content"]["media"],
                relationships=payload["relationships"],
                metrics=payload["metrics"],
                source_metadata=payload["source_metadata"],
            )
            .on_conflict_do_nothing(constraint="uq_event_platform_post")
            .returning(SocialEvent.event_id)
        )
        event_id = self.session.execute(statement).scalar_one_or_none()
        created = event_id is not None
        if event_id is None:
            event_id = self.session.execute(
                select(SocialEvent.event_id).where(
                    SocialEvent.platform == event.platform.value,
                    SocialEvent.platform_post_id == event.platform_post_id,
                )
            ).scalar_one()
        self.session.commit()
        return EventWriteResult(event_id=event_id, created=created)

    def get_event(self, event_id: UUID) -> CanonicalEvent | None:
        row = self.session.execute(self._event_query().where(SocialEvent.event_id == event_id)).one_or_none()
        return self._to_event(row) if row else None

    def list_events(
        self,
        *,
        limit: int = 100,
        platform: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        newest_first: bool = False,
        offset: int = 0,
    ) -> list[CanonicalEvent]:
        query = self._event_query()
        if platform:
            query = query.where(SocialEvent.platform == platform)
        if start:
            query = query.where(SocialEvent.created_at >= start)
        if end:
            query = query.where(SocialEvent.created_at < end)
        ordering = SocialEvent.created_at.desc() if newest_first else SocialEvent.created_at.asc()
        rows = self.session.execute(
            query.order_by(ordering).offset(offset).limit(limit)
        ).all()
        return [self._to_event(row) for row in rows]

    def list_enriched_events(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        platform: str | None = None,
        search: str | None = None,
        sentiment: str | None = None,
        emotion: str | None = None,
        interaction: str | None = None,
        newest_first: bool = True,
    ) -> list[tuple[CanonicalEvent, NLPResult | None]]:
        query = self._event_query().outerjoin(
            NLPAnalysis, NLPAnalysis.event_id == SocialEvent.event_id
        ).add_columns(NLPAnalysis)
        query = self._filter_enriched_query(
            query, platform=platform, search=search, sentiment=sentiment,
            emotion=emotion, interaction=interaction,
        )
        ordering = SocialEvent.created_at.desc() if newest_first else SocialEvent.created_at.asc()
        rows = self.session.execute(
            query.order_by(ordering, SocialEvent.event_id.desc()).offset(offset).limit(limit)
        ).all()
        return [
            (
                self._to_event(row[:2]),
                NLPResult.from_orm_record(row[2]) if row[2] is not None else None,
            )
            for row in rows
        ]

    def count_enriched_events(
        self,
        *,
        platform: str | None = None,
        search: str | None = None,
        sentiment: str | None = None,
        emotion: str | None = None,
        interaction: str | None = None,
    ) -> int:
        query = select(func.count()).select_from(SocialEvent).join(
            SocialUser, SocialUser.user_id == SocialEvent.author_id
        ).outerjoin(NLPAnalysis, NLPAnalysis.event_id == SocialEvent.event_id)
        query = self._filter_enriched_query(
            query, platform=platform, search=search, sentiment=sentiment,
            emotion=emotion, interaction=interaction,
        )
        return self.session.execute(query).scalar_one()

    @staticmethod
    def _filter_enriched_query(
        query: Select,
        *,
        platform: str | None,
        search: str | None,
        sentiment: str | None,
        emotion: str | None,
        interaction: str | None,
    ) -> Select:
        if platform:
            query = query.where(SocialEvent.platform == platform)
        if interaction:
            query = query.where(SocialEvent.interaction_type == interaction)
        if sentiment:
            query = query.where(NLPAnalysis.sentiment_label == sentiment)
        if emotion:
            query = query.where(NLPAnalysis.primary_emotion == emotion)
        if search:
            # Treat user input as a literal substring, not as LIKE wildcards.
            escaped = search.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped}%"
            query = query.where(or_(
                SocialEvent.content_text.ilike(pattern, escape="\\"),
                SocialUser.username.ilike(pattern, escape="\\"),
                SocialUser.display_name.ilike(pattern, escape="\\"),
                func.array_to_string(SocialEvent.hashtags, " ").ilike(pattern, escape="\\"),
            ))
        return query

    def count_events(self, *, platform: str | None = None) -> int:
        query = select(func.count()).select_from(SocialEvent)
        if platform:
            query = query.where(SocialEvent.platform == platform)
        return self.session.execute(query).scalar_one()

    def count_events_by_replay(self, *, replay: bool) -> int:
        replay_value = SocialEvent.source_metadata["replay"].as_boolean()
        return self.session.scalar(
            select(func.count())
            .select_from(SocialEvent)
            .where(func.coalesce(replay_value, False).is_(replay))
        ) or 0

    def platform_event_summaries(self) -> list[dict]:
        replay_value = SocialEvent.source_metadata["replay"].as_boolean()
        rows = self.session.execute(
            select(
                SocialEvent.platform,
                func.count().label("event_count"),
                func.count().filter(func.coalesce(replay_value, False).is_(False)).label(
                    "real_event_count"
                ),
                func.count().filter(func.coalesce(replay_value, False).is_(True)).label(
                    "replay_event_count"
                ),
                func.max(SocialEvent.created_at).label("latest_created_at"),
                func.max(SocialEvent.collected_at).label("latest_collected_at"),
            )
            .group_by(SocialEvent.platform)
            .order_by(SocialEvent.platform)
        ).all()
        return [dict(row._mapping) for row in rows]

    def list_events_without_nlp(self, *, limit: int = 100) -> list[CanonicalEvent]:
        query = (
            self._event_query()
            .outerjoin(NLPAnalysis, NLPAnalysis.event_id == SocialEvent.event_id)
            .where(NLPAnalysis.event_id.is_(None))
            .order_by(SocialEvent.created_at.asc())
            .limit(limit)
        )
        return [self._to_event(row) for row in self.session.execute(query).all()]

    def list_events_without_graph(self, *, limit: int = 100) -> list[CanonicalEvent]:
        query = (
            self._event_query()
            .where(SocialEvent.graph_processed_at.is_(None))
            .order_by(SocialEvent.created_at.asc())
            .limit(limit)
        )
        return [self._to_event(row) for row in self.session.execute(query).all()]

    def mark_graph_processed(self, event_id: UUID, processed_at: datetime) -> None:
        self.session.execute(
            update(SocialEvent)
            .where(SocialEvent.event_id == event_id)
            .values(graph_processed_at=processed_at)
        )

    def latest_collected_at(self, *, include_replay: bool = False) -> datetime | None:
        query = select(func.max(SocialEvent.collected_at))
        if not include_replay:
            replay_value = SocialEvent.source_metadata["replay"].as_boolean()
            query = query.where(func.coalesce(replay_value, False).is_(False))
        return self.session.scalar(query)

    def commit(self) -> None:
        self.session.commit()

    def record_dead_letter(
        self,
        *,
        platform: str | None,
        error_type: str,
        error_message: str,
        raw_payload: dict | None = None,
    ) -> UUID:
        dead_letter = DeadLetterEvent(
            platform=platform,
            error_type=error_type,
            error_message=error_message,
            raw_payload=raw_payload,
        )
        self.session.add(dead_letter)
        self.session.commit()
        return dead_letter.dead_letter_id

    def upsert_nlp_result(self, event_id: UUID, result: NLPResult) -> None:
        values = result.to_persistence(event_id)
        statement = insert(NLPAnalysis).values(**values)
        update_values = {key: value for key, value in values.items() if key not in {"analysis_id", "event_id"}}
        self.session.execute(
            statement.on_conflict_do_update(constraint="uq_nlp_event", set_=update_values)
        )
        self.session.commit()

    def list_nlp_results(
        self,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        platform: str | None = None,
    ) -> list[tuple[CanonicalEvent, NLPResult]]:
        query = self._event_query().join(NLPAnalysis, NLPAnalysis.event_id == SocialEvent.event_id)
        query = query.add_columns(NLPAnalysis)
        if start:
            query = query.where(SocialEvent.created_at >= start)
        if end:
            query = query.where(SocialEvent.created_at < end)
        if platform:
            query = query.where(SocialEvent.platform == platform)
        rows = self.session.execute(query.order_by(SocialEvent.created_at.asc())).all()
        output: list[tuple[CanonicalEvent, NLPResult]] = []
        for row in rows:
            event = self._to_event(row[:2])
            output.append((event, NLPResult.from_orm_record(row[2])))
        return output

    def insert_graph_edges(self, edges: list[EdgeRecord]) -> int:
        inserted = 0
        for edge in edges:
            statement = (
                insert(GraphEdge)
                .values(**edge.model_dump())
                .on_conflict_do_nothing(constraint="uq_graph_event_relation")
                .returning(GraphEdge.edge_id)
            )
            inserted += int(self.session.execute(statement).scalar_one_or_none() is not None)
        self.session.commit()
        return inserted

    def list_graph_edges(
        self,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        include_replay: bool = True,
        platform: str | None = None,
        limit: int | None = None,
        newest_first: bool = False,
    ) -> list[EdgeRecord]:
        query = select(GraphEdge).join(SocialEvent, SocialEvent.event_id == GraphEdge.event_id)
        if not include_replay:
            replay_value = SocialEvent.source_metadata["replay"].as_boolean()
            query = query.where(func.coalesce(replay_value, False).is_(False))
        if platform:
            query = query.where(GraphEdge.platform == platform)
        if start:
            query = query.where(GraphEdge.occurred_at >= start)
        if end:
            query = query.where(GraphEdge.occurred_at < end)
        ordering = GraphEdge.occurred_at.desc() if newest_first else GraphEdge.occurred_at.asc()
        query = query.order_by(ordering)
        if limit is not None:
            query = query.limit(limit)
        return [EdgeRecord.model_validate(row) for row in self.session.scalars(query).all()]

    def list_cascade_records(
        self,
        *,
        platform: str | None = None,
        limit: int = 10_000,
    ) -> list[tuple[SocialEvent, str]]:
        """Stored events with parent/thread references plus author labels."""
        query = (
            select(SocialEvent, SocialUser.platform_user_id)
            .join(SocialUser, SocialUser.user_id == SocialEvent.author_id)
            .where(SocialEvent.thread_root_id.isnot(None))
        )
        if platform:
            query = query.where(SocialEvent.platform == platform)
        rows = self.session.execute(
            query.order_by(SocialEvent.created_at.asc()).limit(limit)
        ).all()
        return [(row[0], f"{row[0].platform}:{row[1]}") for row in rows]

    def nlp_map_for_events(self, event_ids: list[UUID]) -> dict[UUID, NLPAnalysis]:
        if not event_ids:
            return {}
        rows = self.session.scalars(
            select(NLPAnalysis).where(NLPAnalysis.event_id.in_(event_ids))
        ).all()
        return {row.event_id: row for row in rows}

    @staticmethod
    def _event_query() -> Select:
        return select(SocialEvent, SocialUser).join(SocialUser, SocialUser.user_id == SocialEvent.author_id)

    @staticmethod
    def _to_event(row: object) -> CanonicalEvent:
        event: SocialEvent = row[0]  # type: ignore[index]
        user: SocialUser = row[1]  # type: ignore[index]
        return CanonicalEvent(
            event_id=event.event_id,
            platform=event.platform,
            platform_post_id=event.platform_post_id,
            parent_platform_post_id=event.parent_platform_post_id,
            thread_root_id=event.thread_root_id,
            interaction_type=event.interaction_type,
            created_at=event.created_at,
            collected_at=event.collected_at,
            author=AuthorInfo(
                platform_user_id=user.platform_user_id,
                username=user.username,
                display_name=user.display_name,
                bio=user.bio,
                location_raw=user.location_raw,
                avatar_url=user.avatar_url,
                followers_count=user.followers_count,
                following_count=user.following_count,
                is_verified=user.is_verified,
            ),
            content=ContentInfo(
                text=event.content_text,
                language=event.language_code,
                hashtags=event.hashtags,
                mentions=event.mentions,
                media=[MediaInfo.model_validate(item) for item in event.media],
            ),
            relationships=RelationshipInfo.model_validate(event.relationships),
            metrics=EngagementMetrics.model_validate(event.metrics),
            source_metadata=event.source_metadata,
        )
