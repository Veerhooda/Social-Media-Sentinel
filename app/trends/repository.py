from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, exists, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.models import NLPAnalysis, SocialEvent, Topic, TrendMeasurement
from app.trends.schemas import (
    TopicCatalogEntry,
    TopicDetail,
    TopicEvolutionPoint,
    TopicSummary,
    TrendDocument,
)


class TrendRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_documents(
        self,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        platform: str | None = None,
        include_replay: bool = False,
        limit: int = 10_000,
    ) -> list[TrendDocument]:
        query = select(SocialEvent, NLPAnalysis).outerjoin(
            NLPAnalysis, NLPAnalysis.event_id == SocialEvent.event_id
        )
        query = query.where(func.length(func.trim(SocialEvent.content_text)) > 0)
        if not include_replay:
            replay_value = SocialEvent.source_metadata["replay"].as_boolean()
            query = query.where(func.coalesce(replay_value, False).is_(False))
        if start:
            query = query.where(SocialEvent.created_at >= start)
        if end:
            query = query.where(SocialEvent.created_at < end)
        if platform:
            query = query.where(SocialEvent.platform == platform)
        rows = self.session.execute(
            query.order_by(SocialEvent.created_at.asc()).limit(limit)
        ).all()
        return [
            TrendDocument(
                event_id=event.event_id,
                platform=event.platform,
                text=event.content_text.strip(),
                created_at=event.created_at,
                sentiment_label=analysis.sentiment_label if analysis else None,
            )
            for event, analysis in rows
        ]

    def list_catalog(self) -> list[TopicCatalogEntry]:
        topics = self.session.scalars(
            select(Topic).where(Topic.topic_key.is_not(None)).order_by(Topic.topic_id)
        ).all()
        return [
            TopicCatalogEntry(
                topic_id=topic.topic_id,
                topic_key=topic.topic_key,
                name=topic.name,
                keywords=topic.keywords,
            )
            for topic in topics
            if topic.topic_key is not None
        ]

    def prepare_windows(self, window_starts: set[datetime], analysis_engine: str) -> None:
        """Replace one engine's derived window state without touching source events."""
        if not window_starts:
            return
        self.session.execute(
            delete(TrendMeasurement).where(
                TrendMeasurement.window_start.in_(window_starts),
                TrendMeasurement.analysis_engine == analysis_engine,
            )
        )

    def delete_orphan_topics(self, analysis_engine: str) -> None:
        remaining_measurement = exists(
            select(TrendMeasurement.measurement_id).where(
                TrendMeasurement.topic_id == Topic.topic_id
            )
        )
        self.session.execute(
            delete(Topic).where(
                Topic.model_name == analysis_engine,
                ~remaining_measurement,
            )
        )

    def upsert_topic(
        self,
        *,
        topic_key: str,
        name: str,
        keywords: list[str],
        model_name: str,
        first_seen_at: datetime,
        last_seen_at: datetime,
    ) -> int:
        statement = insert(Topic).values(
            topic_key=topic_key,
            name=name,
            keywords=keywords,
            model_name=model_name,
            first_seen_at=first_seen_at,
            last_seen_at=last_seen_at,
        )
        excluded = statement.excluded
        statement = statement.on_conflict_do_update(
            constraint="uq_topic_key",
            set_={
                "name": excluded.name,
                "keywords": excluded.keywords,
                "model_name": excluded.model_name,
                "first_seen_at": func.least(Topic.first_seen_at, excluded.first_seen_at),
                "last_seen_at": func.greatest(Topic.last_seen_at, excluded.last_seen_at),
            },
        ).returning(Topic.topic_id)
        return self.session.execute(statement).scalar_one()

    def upsert_measurement(
        self,
        *,
        topic_id: int,
        window_start: datetime,
        window_end: datetime,
        document_count: int,
        growth_score: float | None,
        velocity_score: float | None,
        acceleration_score: float | None,
        status: str,
        sentiment_distribution: dict[str, float],
        analysis_engine: str,
    ) -> None:
        values = {
            "topic_id": topic_id,
            "window_start": window_start,
            "window_end": window_end,
            "document_count": document_count,
            "growth_score": growth_score,
            "velocity_score": velocity_score,
            "acceleration_score": acceleration_score,
            "status": status,
            "sentiment_distribution": sentiment_distribution,
            "analysis_engine": analysis_engine,
        }
        statement = insert(TrendMeasurement).values(**values)
        self.session.execute(
            statement.on_conflict_do_update(
                constraint="uq_trend_topic_window",
                set_={key: value for key, value in values.items() if key != "topic_id"},
            )
        )

    def latest_measurement_before(
        self, topic_id: int, before: datetime
    ) -> TrendMeasurement | None:
        return self.session.scalar(
            select(TrendMeasurement)
            .where(
                TrendMeasurement.topic_id == topic_id,
                TrendMeasurement.window_end <= before,
            )
            .order_by(TrendMeasurement.window_end.desc())
            .limit(1)
        )

    def commit(self) -> None:
        self.session.commit()

    def list_topics(self) -> list[TopicSummary]:
        topics = self.session.scalars(
            select(Topic).order_by(Topic.last_seen_at.desc(), Topic.topic_id.asc())
        ).all()
        summaries: list[TopicSummary] = []
        for topic in topics:
            measurement = self._latest_measurement(topic.topic_id)
            if measurement is not None:
                summaries.append(self._to_summary(topic, measurement))
        return summaries

    def get_topic(self, topic_id: int) -> TopicDetail | None:
        topic = self.session.get(Topic, topic_id)
        if topic is None:
            return None
        evolution = self.get_evolution(topic_id)
        latest = self._latest_measurement(topic_id)
        if latest is None:
            return TopicDetail(
                topic_id=topic.topic_id,
                topic=topic.name,
                keywords=topic.keywords,
                volume=0,
                status="emerging",
                model_name=topic.model_name,
                first_seen_at=topic.first_seen_at,
                last_seen_at=topic.last_seen_at,
                evolution=evolution,
            )
        summary = self._to_summary(topic, latest)
        return TopicDetail(
            **summary.model_dump(),
            model_name=topic.model_name,
            first_seen_at=topic.first_seen_at,
            last_seen_at=topic.last_seen_at,
            evolution=evolution,
        )

    def get_evolution(self, topic_id: int) -> list[TopicEvolutionPoint]:
        measurements = self.session.scalars(
            select(TrendMeasurement)
            .where(TrendMeasurement.topic_id == topic_id)
            .order_by(TrendMeasurement.window_start.asc())
        ).all()
        return [
            TopicEvolutionPoint(
                window_start=item.window_start,
                window_end=item.window_end,
                volume=item.document_count,
                growth=item.growth_score,
                velocity=item.velocity_score,
                acceleration=item.acceleration_score,
                status=item.status or "emerging",
                sentiment=item.sentiment_distribution or {},
            )
            for item in measurements
        ]

    def count_topics(self) -> int:
        return self.session.scalar(select(func.count()).select_from(Topic)) or 0

    def count_measurements(self) -> int:
        return self.session.scalar(select(func.count()).select_from(TrendMeasurement)) or 0

    def _latest_measurement(self, topic_id: int) -> TrendMeasurement | None:
        return self.session.scalar(
            select(TrendMeasurement)
            .where(TrendMeasurement.topic_id == topic_id)
            .order_by(TrendMeasurement.window_end.desc())
            .limit(1)
        )

    @staticmethod
    def _to_summary(topic: Topic, item: TrendMeasurement) -> TopicSummary:
        return TopicSummary(
            topic_id=topic.topic_id,
            topic=topic.name,
            keywords=topic.keywords,
            volume=item.document_count,
            growth=item.growth_score,
            velocity=item.velocity_score,
            acceleration=item.acceleration_score,
            window_start=item.window_start,
            window_end=item.window_end,
            status=item.status or "emerging",
            sentiment=item.sentiment_distribution or {},
            source=item.analysis_engine or "bertrend",
        )
