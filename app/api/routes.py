from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError

from app.analytics.aggregation import hashtag_trends
from app.analytics.temporal import aggregate_daily, aggregate_rolling
from app.api.dependencies import get_repository
from app.api.schemas import (
    ComponentHealth,
    EventListResponse,
    HealthResponse,
    LiveEventsResponse,
    NetworkResponse,
    TemporalSeriesResponse,
    TrendAnalyticsResponse,
)
from app.db.repositories.social import SocialRepository
from app.graph.builder import GraphBuilder
from app.graph.metrics import calculate_network_metrics
from app.models.events import CanonicalEvent
from app.platforms.x.adapter import XAdapter
from app.trends.repository import TrendRepository
from app.trends.schemas import (
    AnalysisStatus,
    TopicDetail,
    TopicEvolutionResponse,
    TopicListResponse,
    TopicSummary,
)

router = APIRouter(prefix="/api")


@router.get("/health", response_model=HealthResponse)
def health(repository: SocialRepository = Depends(get_repository)) -> HealthResponse:
    try:
        db_ok = repository.health_check()
        event_count = repository.count_events()
        database = ComponentHealth(status="PASS" if db_ok else "FAIL", detail="PostgreSQL reachable")
    except SQLAlchemyError as exc:
        return HealthResponse(
            status="FAIL",
            database=ComponentHealth(status="FAIL", detail=str(exc)),
            x_api=ComponentHealth(status="SKIPPED", detail="Database health failed first"),
            event_count=0,
        )
    x_health = XAdapter().health_check(live=False)
    x_status = x_health.status if x_health.status in {"PASS", "FAIL", "SKIPPED", "UNAVAILABLE"} else "FAIL"
    return HealthResponse(
        status="PASS" if x_status == "PASS" else "DEGRADED",
        database=database,
        x_api=ComponentHealth(status=x_status, detail=x_health.detail),  # type: ignore[arg-type]
        event_count=event_count,
    )


@router.get("/events", response_model=EventListResponse)
def list_events(
    limit: int = Query(default=100, ge=1, le=1000),
    platform: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    repository: SocialRepository = Depends(get_repository),
) -> EventListResponse:
    items = repository.list_events(limit=limit, platform=platform, start=start, end=end)
    return EventListResponse(items=items, count=len(items))


@router.get("/events/live", response_model=LiveEventsResponse)
def live_events(
    limit: int = Query(default=25, ge=1, le=100),
    repository: SocialRepository = Depends(get_repository),
) -> LiveEventsResponse:
    items = repository.list_events(limit=limit, newest_first=True)
    replay_count = sum(bool(item.source_metadata.get("replay")) for item in items)
    live_count = len(items) - replay_count
    if replay_count and live_count:
        return LiveEventsResponse(
            mode="mixed", label="Live X and historical replay data", items=items
        )
    if items and replay_count:
        return LiveEventsResponse(mode="replay", label="Historical replay data", items=items)
    if live_count:
        return LiveEventsResponse(mode="live", label="Real X data", items=items)
    return LiveEventsResponse(mode="idle", label="No active live stream", items=items)


@router.get("/events/{event_id}", response_model=CanonicalEvent)
def get_event(
    event_id: UUID, repository: SocialRepository = Depends(get_repository)
):
    event = repository.get_event(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


def _temporal_response(repository: SocialRepository) -> TemporalSeriesResponse:
    records = repository.list_nlp_results()
    return TemporalSeriesResponse(
        rolling_1h=aggregate_rolling(records),
        daily=aggregate_daily(records),
    )


@router.get("/analytics/sentiment", response_model=TemporalSeriesResponse)
def sentiment(repository: SocialRepository = Depends(get_repository)) -> TemporalSeriesResponse:
    return _temporal_response(repository)


@router.get("/analytics/emotions", response_model=TemporalSeriesResponse)
def emotions(repository: SocialRepository = Depends(get_repository)) -> TemporalSeriesResponse:
    return _temporal_response(repository)


@router.get("/analytics/trends", response_model=TrendAnalyticsResponse)
def trends(
    repository: SocialRepository = Depends(get_repository),
) -> TrendAnalyticsResponse:
    trend_repository = TrendRepository(repository.session)
    persisted = trend_repository.list_topics()
    if persisted:
        temporal_status = (
            AnalysisStatus.PASS
            if any(item.velocity is not None for item in persisted)
            else AnalysisStatus.INSUFFICIENT_DATA
        )
        return TrendAnalyticsResponse(
            status=AnalysisStatus.PASS,
            temporal_status=temporal_status,
            engine=persisted[0].source,
            fallback=False,
            items=persisted,
            detail=(
                None
                if temporal_status is AnalysisStatus.PASS
                else "Topics exist, but fewer than two comparable measurements are available"
            ),
        )

    events = repository.list_events(limit=1000)
    fallback_items = hashtag_trends(events)
    return TrendAnalyticsResponse(
        status=AnalysisStatus.SKIPPED,
        temporal_status=AnalysisStatus.INSUFFICIENT_DATA,
        engine="hashtag_frequency",
        fallback=True,
        items=[
            TopicSummary(
                topic=item.topic,
                volume=item.volume,
                status="fallback",
                source=item.source,
            )
            for item in fallback_items
        ],
        detail="No persisted BERTrend measurements; returning the explicit frequency fallback",
    )


@router.get("/analytics/topics", response_model=TopicListResponse)
def topics(repository: SocialRepository = Depends(get_repository)) -> TopicListResponse:
    items = TrendRepository(repository.session).list_topics()
    return TopicListResponse(
        status=AnalysisStatus.PASS if items else AnalysisStatus.INSUFFICIENT_DATA,
        engine=items[0].source if items else "BERTrend",
        items=items,
        detail=None if items else "No persisted BERTrend topics",
    )


@router.get("/analytics/topics/{topic_id}", response_model=TopicDetail)
def topic_detail(
    topic_id: int, repository: SocialRepository = Depends(get_repository)
) -> TopicDetail:
    topic = TrendRepository(repository.session).get_topic(topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    return topic


@router.get(
    "/analytics/topics/{topic_id}/evolution", response_model=TopicEvolutionResponse
)
def topic_evolution(
    topic_id: int, repository: SocialRepository = Depends(get_repository)
) -> TopicEvolutionResponse:
    trend_repository = TrendRepository(repository.session)
    topic = trend_repository.get_topic(topic_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    items = topic.evolution
    return TopicEvolutionResponse(
        status=(
            AnalysisStatus.PASS if len(items) >= 2 else AnalysisStatus.INSUFFICIENT_DATA
        ),
        topic_id=topic_id,
        topic=topic.topic,
        items=items,
        detail=None if len(items) >= 2 else "At least two measurements are required for evolution",
    )


@router.get("/network/summary", response_model=NetworkResponse)
def network_summary(repository: SocialRepository = Depends(get_repository)) -> NetworkResponse:
    graph = GraphBuilder.build_graph(repository.list_graph_edges())
    return NetworkResponse(summary=calculate_network_metrics(graph))
