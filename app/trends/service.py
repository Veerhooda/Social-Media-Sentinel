from __future__ import annotations

import hashlib
from collections import Counter
from datetime import datetime, timedelta
from typing import Protocol

from app.core.config import Settings, get_settings
from app.trends.batching import create_micro_batches
from app.trends.berttrend import BERTrendAnalyzer
from app.trends.repository import TrendRepository
from app.trends.schemas import (
    AnalysisStatus,
    BackendAnalysisResult,
    MicroBatch,
    SignalStatus,
    TopicCatalogEntry,
    TrendDocument,
    TrendRunResult,
)


class TrendAnalyzer(Protocol):
    engine_name: str

    def analyze(self, batches: list[MicroBatch]) -> BackendAnalysisResult: ...


class TrendService:
    def __init__(
        self,
        repository: TrendRepository,
        analyzer: TrendAnalyzer | None = None,
        settings: Settings | None = None,
    ):
        self.repository = repository
        self.settings = settings or get_settings()
        self.analyzer = analyzer or BERTrendAnalyzer(
            embedding_model_name=self.settings.trend_embedding_model,
            min_documents=self.settings.trend_min_documents,
            allow_download=self.settings.trend_model_download_enabled,
            match_similarity=self.settings.trend_topic_centroid_similarity_threshold,
        )

    def run(
        self,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        platform: str | None = None,
        include_replay: bool = False,
    ) -> TrendRunResult:
        documents = self.repository.list_documents(
            start=start,
            end=end,
            platform=platform,
            include_replay=include_replay,
        )
        window = timedelta(minutes=self.settings.trend_window_minutes)
        batches = create_micro_batches(documents, window=window)
        if not documents:
            return TrendRunResult(
                status=AnalysisStatus.SKIPPED,
                temporal_status=AnalysisStatus.INSUFFICIENT_DATA,
                engine=self.analyzer.engine_name,
                documents=0,
                batches=0,
                eligible_batches=0,
                topics_discovered=0,
                topics_matched_across_windows=0,
                topics_persisted=0,
                measurements_persisted=0,
                detail="No canonical event text matched the requested range",
            )

        backend_result = self.analyzer.analyze(batches)
        if backend_result.status is not AnalysisStatus.PASS:
            return TrendRunResult(
                status=backend_result.status,
                temporal_status=AnalysisStatus.INSUFFICIENT_DATA,
                engine=backend_result.engine,
                documents=len(documents),
                batches=len(batches),
                eligible_batches=backend_result.eligible_batches,
                topics_discovered=0,
                topics_matched_across_windows=0,
                topics_persisted=0,
                measurements_persisted=0,
                detail=backend_result.detail,
            )

        analyzed_windows = {topic.window_start for topic in backend_result.topics}
        self.repository.prepare_windows(analyzed_windows, backend_result.engine)
        documents_by_id = {document.event_id: document for document in documents}
        catalog = self.repository.list_catalog()
        persisted_topic_ids: set[int] = set()
        velocity_measurements = 0
        measurement_windows: set[datetime] = set()

        for discovered in sorted(
            backend_result.topics, key=lambda item: (item.window_start, item.local_topic_id)
        ):
            lineage_key = discovered.lineage_key or self._topic_key(discovered.keywords)
            match = next(
                (topic for topic in catalog if topic.topic_key == lineage_key), None
            ) or self._find_match(discovered.keywords, catalog)
            topic_key = match.topic_key if match else lineage_key
            topic_id = self.repository.upsert_topic(
                topic_key=topic_key,
                name=discovered.name,
                keywords=discovered.keywords,
                model_name=backend_result.engine,
                first_seen_at=discovered.window_start,
                last_seen_at=discovered.window_end,
            )
            if match is None:
                catalog.append(
                    TopicCatalogEntry(
                        topic_id=topic_id,
                        topic_key=topic_key,
                        name=discovered.name,
                        keywords=discovered.keywords,
                    )
                )

            previous = self.repository.latest_measurement_before(
                topic_id, discovered.window_start
            )
            document_count = len(discovered.document_ids)
            growth, velocity, acceleration, signal_status = self._measurement_values(
                document_count=document_count,
                previous=previous,
                window=window,
                current_window_start=discovered.window_start,
            )
            sentiment = self._sentiment_distribution(
                [documents_by_id[event_id] for event_id in discovered.document_ids]
            )
            self.repository.upsert_measurement(
                topic_id=topic_id,
                window_start=discovered.window_start,
                window_end=discovered.window_end,
                document_count=document_count,
                growth_score=growth,
                velocity_score=velocity,
                acceleration_score=acceleration,
                status=signal_status.value,
                sentiment_distribution=sentiment,
                analysis_engine=backend_result.engine,
            )
            persisted_topic_ids.add(topic_id)
            measurement_windows.add(discovered.window_start)
            velocity_measurements += int(velocity is not None)

        self.repository.delete_orphan_topics(backend_result.engine)
        self.repository.commit()
        temporal_status = (
            AnalysisStatus.PASS
            if len(measurement_windows) >= 2 and velocity_measurements
            else AnalysisStatus.INSUFFICIENT_DATA
        )
        detail = backend_result.detail
        if temporal_status is AnalysisStatus.INSUFFICIENT_DATA:
            detail = (
                f"{detail}; topic discovery passed, but at least two populated windows "
                "are required for growth/velocity"
            )
        return TrendRunResult(
            status=AnalysisStatus.PASS,
            temporal_status=temporal_status,
            engine=backend_result.engine,
            documents=len(documents),
            batches=len(batches),
            eligible_batches=backend_result.eligible_batches,
            topics_discovered=len(backend_result.topics),
            topics_matched_across_windows=backend_result.matched_topics,
            topics_persisted=len(persisted_topic_ids),
            measurements_persisted=len(backend_result.topics),
            detail=detail,
        )

    def _find_match(
        self, keywords: list[str], catalog: list[TopicCatalogEntry]
    ) -> TopicCatalogEntry | None:
        normalized = {word.casefold() for word in keywords if word}
        best: TopicCatalogEntry | None = None
        best_score = 0.0
        for topic in catalog:
            existing = {word.casefold() for word in topic.keywords if word}
            union = normalized | existing
            score = len(normalized & existing) / len(union) if union else 0.0
            if score > best_score:
                best = topic
                best_score = score
        return (
            best
            if best is not None
            and best_score >= self.settings.trend_topic_similarity_threshold
            else None
        )

    @staticmethod
    def _topic_key(keywords: list[str]) -> str:
        normalized = "|".join(sorted({word.casefold() for word in keywords if word}))
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:32]

    @staticmethod
    def _measurement_values(
        *,
        document_count: int,
        previous: object | None,
        window: timedelta,
        current_window_start: datetime | None = None,
    ) -> tuple[float | None, float | None, float | None, SignalStatus]:
        if previous is None:
            return None, None, None, SignalStatus.EMERGING
        previous_count = int(previous.document_count)
        change = document_count - previous_count
        growth = change / max(previous_count, 1)
        elapsed = window
        previous_window_start = getattr(previous, "window_start", None)
        if current_window_start is not None and previous_window_start is not None:
            candidate = current_window_start - previous_window_start
            if candidate.total_seconds() > 0:
                elapsed = candidate
        hours = elapsed.total_seconds() / 3600
        velocity = change / hours
        previous_velocity = previous.velocity_score
        acceleration = (
            (velocity - float(previous_velocity)) / hours
            if previous_velocity is not None
            else None
        )
        if growth >= 1:
            status = SignalStatus.EXPLOSIVE
        elif growth > 0:
            status = SignalStatus.RISING
        elif growth == 0:
            status = SignalStatus.SUSTAINED
        else:
            status = SignalStatus.COOLING
        return growth, velocity, acceleration, status

    @staticmethod
    def _sentiment_distribution(documents: list[TrendDocument]) -> dict[str, float]:
        counts = Counter(
            document.sentiment_label
            for document in documents
            if document.sentiment_label is not None
        )
        total = sum(counts.values())
        return {label: count / total for label, count in counts.items()} if total else {}
