from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.exc import SQLAlchemyError

from app.analytics.aggregation import hashtag_trends
from app.analytics.temporal import aggregate_daily, aggregate_rolling
from app.api.dependencies import get_repository
from app.api.schemas import (
    ComponentHealth,
    EnrichedEvent,
    EnrichedEventListResponse,
    EventListResponse,
    HealthResponse,
    LiveEventsResponse,
    NetworkGraphEdge,
    NetworkGraphResponse,
    NetworkResponse,
    PlatformDataSummary,
    SchedulerStatus,
    TemporalSeriesResponse,
    TrendAnalyticsResponse,
)
from app.db.repositories.social import SocialRepository
from app.demographics.geography import country_label_for_code
from app.demographics.repository import DemographicRepository
from app.demographics.schemas import (
    DemographicsResponse,
    DimensionDistribution,
    UserDemographicSignal,
)
from app.demographics.service import DemographicService
from app.graph.builder import GraphBuilder
from app.graph.cascades import (
    CascadeEvent,
    propagation_path,
    reconstruct_cascades,
    sentiment_composition,
)
from app.graph.communities import community_profiles, detect_communities
from app.graph.metrics import calculate_network_metrics
from app.graph.snapshots import build_snapshots, influence_changes
from app.models.events import CanonicalEvent
from app.platforms.telegram.adapter import TelegramAdapter
from app.platforms.x.adapter import XAdapter
from app.platforms.youtube.adapter import YouTubeAdapter
from app.scheduler.jobs import GRAPH_JOB, NLP_JOB, TREND_JOB, X_COLLECTION_JOB
from app.scheduler.schemas import JobRunStatus
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
def health(
    request: Request,
    repository: SocialRepository = Depends(get_repository),
) -> HealthResponse:
    scheduler_service = getattr(request.app.state, "scheduler", None)
    scheduler_snapshot = scheduler_service.snapshot() if scheduler_service else None
    if scheduler_snapshot is None:
        scheduler_health = ComponentHealth(
            status="UNAVAILABLE", detail="Scheduler is not initialized"
        )
        analytics_health = ComponentHealth(
            status="UNAVAILABLE", detail="Analytical jobs are not initialized"
        )
    elif not scheduler_snapshot.enabled:
        scheduler_health = ComponentHealth(
            status="SKIPPED", detail="Scheduler is disabled by configuration"
        )
        analytics_health = ComponentHealth(
            status="SKIPPED", detail="Scheduled analytical jobs are disabled"
        )
    else:
        failed = [job.name for job in scheduler_snapshot.jobs if job.status is JobRunStatus.FAIL]
        scheduler_health = ComponentHealth(
            status="FAIL" if failed or not scheduler_snapshot.running else "PASS",
            detail=(
                f"Failed jobs: {', '.join(failed)}"
                if failed
                else "Scheduler running" if scheduler_snapshot.running else "Scheduler stopped"
            ),
        )
        analytical_jobs = [
            job
            for job in scheduler_snapshot.jobs
            if job.name in {NLP_JOB, TREND_JOB, GRAPH_JOB}
        ]
        analytical_failures = [job.name for job in analytical_jobs if job.status is JobRunStatus.FAIL]
        analytical_runs = sum(job.run_count for job in analytical_jobs)
        analytics_health = ComponentHealth(
            status=(
                "FAIL"
                if analytical_failures
                else "PASS" if analytical_runs else "SKIPPED"
            ),
            detail=(
                f"Failed analytical jobs: {', '.join(analytical_failures)}"
                if analytical_failures
                else f"Analytical job runs: {analytical_runs}"
            ),
        )
    try:
        db_ok = repository.health_check()
        event_count = repository.count_events()
        real_event_count = repository.count_events_by_replay(replay=False)
        replay_event_count = repository.count_events_by_replay(replay=True)
        database = ComponentHealth(status="PASS" if db_ok else "FAIL", detail="PostgreSQL reachable")
    except SQLAlchemyError as exc:
        return HealthResponse(
            status="FAIL",
            database=ComponentHealth(status="FAIL", detail=str(exc)),
            x_api=ComponentHealth(status="SKIPPED", detail="Database health failed first"),
            telegram_api=ComponentHealth(
                status="SKIPPED", detail="Database health failed first"
            ),
            youtube_api=ComponentHealth(
                status="SKIPPED", detail="Database health failed first"
            ),
            scheduler=scheduler_health,
            analytics=analytics_health,
            event_count=0,
            real_event_count=0,
            replay_event_count=0,
            updated_at=datetime.now(UTC),
            platforms=[],
        )

    x_job = (
        next(
            (job for job in scheduler_snapshot.jobs if job.name == X_COLLECTION_JOB),
            None,
        )
        if scheduler_snapshot
        else None
    )
    if x_job is not None and x_job.run_count:
        x_status = (
            "FAIL"
            if x_job.status is JobRunStatus.FAIL
            else "SKIPPED" if x_job.status is JobRunStatus.SKIPPED else "PASS"
        )
        x_detail = x_job.error or x_job.detail or f"Last X job status: {x_job.status.value}"
    else:
        x_health = XAdapter().health_check(live=False)
        x_status = (
            x_health.status
            if x_health.status in {"PASS", "FAIL", "SKIPPED", "UNAVAILABLE"}
            else "FAIL"
        )
        x_detail = x_health.detail
    degraded = any(
        component.status != "PASS"
        for component in [scheduler_health, analytics_health]
    ) or x_status != "PASS"
    telegram_health = TelegramAdapter().configuration_health()
    youtube_health = YouTubeAdapter().configuration_health()
    platform_summaries = [
        PlatformDataSummary.model_validate(item)
        for item in repository.platform_event_summaries()
    ]
    return HealthResponse(
        status="DEGRADED" if degraded else "PASS",
        database=database,
        x_api=ComponentHealth(status=x_status, detail=x_detail),  # type: ignore[arg-type]
        telegram_api=ComponentHealth(
            status=telegram_health.status,
            detail=telegram_health.detail,
        ),
        youtube_api=ComponentHealth(
            status=youtube_health.status,
            detail=youtube_health.detail,
        ),
        scheduler=scheduler_health,
        analytics=analytics_health,
        event_count=event_count,
        real_event_count=real_event_count,
        replay_event_count=replay_event_count,
        updated_at=datetime.now(UTC),
        platforms=platform_summaries,
    )


@router.get("/system/jobs", response_model=SchedulerStatus)
def system_jobs(request: Request) -> SchedulerStatus:
    scheduler_service = getattr(request.app.state, "scheduler", None)
    if scheduler_service is None:
        raise HTTPException(status_code=503, detail="Scheduler is not initialized")
    return scheduler_service.snapshot()


@router.get("/events", response_model=EventListResponse)
def list_events(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    platform: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    newest_first: bool = False,
    repository: SocialRepository = Depends(get_repository),
) -> EventListResponse:
    items = repository.list_events(
        limit=limit,
        offset=offset,
        platform=platform,
        start=start,
        end=end,
        newest_first=newest_first,
    )
    return EventListResponse(
        items=items,
        count=len(items),
        total=repository.count_events(platform=platform),
        offset=offset,
        limit=limit,
    )


@router.get("/events/live", response_model=LiveEventsResponse)
def live_events(
    limit: int = Query(default=25, ge=1, le=100),
    platform: str | None = None,
    repository: SocialRepository = Depends(get_repository),
) -> LiveEventsResponse:
    items = repository.list_events(limit=limit, platform=platform, newest_first=True)
    replay_count = sum(bool(item.source_metadata.get("replay")) for item in items)
    live_count = len(items) - replay_count
    if replay_count and live_count:
        return LiveEventsResponse(
            mode="mixed", label="Real platform and historical replay data", items=items
        )
    if items and replay_count:
        return LiveEventsResponse(mode="replay", label="Historical replay data", items=items)
    if live_count:
        platforms = ", ".join(sorted({item.platform.value for item in items}))
        return LiveEventsResponse(mode="live", label=f"Real {platforms} data", items=items)
    return LiveEventsResponse(mode="idle", label="No active live stream", items=items)


@router.get("/events/enriched", response_model=EnrichedEventListResponse)
def enriched_events(
    limit: int = Query(default=50, ge=1, le=250),
    offset: int = Query(default=0, ge=0),
    platform: str | None = None,
    q: str | None = Query(default=None, max_length=200),
    sentiment: str | None = None,
    emotion: str | None = None,
    interaction: str | None = None,
    newest_first: bool = True,
    repository: SocialRepository = Depends(get_repository),
) -> EnrichedEventListResponse:
    rows = repository.list_enriched_events(
        limit=limit,
        offset=offset,
        platform=platform,
        search=q,
        sentiment=sentiment,
        emotion=emotion,
        interaction=interaction,
        newest_first=newest_first,
    )
    return EnrichedEventListResponse(
        items=[EnrichedEvent(event=event, analysis=analysis) for event, analysis in rows],
        count=len(rows),
        total=repository.count_enriched_events(
            platform=platform, search=q, sentiment=sentiment,
            emotion=emotion, interaction=interaction,
        ),
        offset=offset,
        limit=limit,
    )


@router.get("/events/{event_id}", response_model=CanonicalEvent)
def get_event(
    event_id: UUID, repository: SocialRepository = Depends(get_repository)
):
    event = repository.get_event(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


def _temporal_response(
    repository: SocialRepository, *, platform: str | None = None
) -> TemporalSeriesResponse:
    records = repository.list_nlp_results(platform=platform)
    return TemporalSeriesResponse(
        rolling_1h=aggregate_rolling(records),
        daily=aggregate_daily(records),
    )


@router.get("/analytics/sentiment", response_model=TemporalSeriesResponse)
def sentiment(
    platform: str | None = None,
    repository: SocialRepository = Depends(get_repository),
) -> TemporalSeriesResponse:
    return _temporal_response(repository, platform=platform)


@router.get("/analytics/emotions", response_model=TemporalSeriesResponse)
def emotions(
    platform: str | None = None,
    repository: SocialRepository = Depends(get_repository),
) -> TemporalSeriesResponse:
    return _temporal_response(repository, platform=platform)


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


def _demographic_signals(repository: SocialRepository, platform: str | None):
    demographic_repository = DemographicRepository(repository.session)
    rows = demographic_repository.list_subjects(platform=platform)
    service = DemographicService()
    signals = []
    for row in rows:
        versions = row.model_versions or {}
        signals.append(
            UserDemographicSignal(
                user_id=row.user_id,
                platform=demographic_repository.subject_platform(row) or "unknown",
                age_bracket=row.age_bracket,
                age_confidence=row.age_confidence,
                age_source=versions.get("age", "unavailable"),
                country=country_label_for_code(row.inferred_country),
                region=row.inferred_region,
                geography_confidence=row.geography_confidence,
                geography_source=versions.get("geography", "unknown"),
                language=row.primary_language,
                language_confidence=row.language_confidence,
                language_source=versions.get("language", "unknown"),
                professional_sector=row.professional_sector,
                profession_confidence=row.profession_confidence,
                profession_source=versions.get("profession", "unknown"),
            )
        )
    return service, signals


@router.get("/analytics/demographics", response_model=DemographicsResponse)
def demographics(
    platform: str | None = None,
    repository: SocialRepository = Depends(get_repository),
) -> DemographicsResponse:
    service, signals = _demographic_signals(repository, platform)
    return service.aggregate(signals)


@router.get("/analytics/demographics/age", response_model=DimensionDistribution)
def demographics_age(
    platform: str | None = None,
    repository: SocialRepository = Depends(get_repository),
) -> DimensionDistribution:
    service, signals = _demographic_signals(repository, platform)
    return service.aggregate(signals).dimensions["age"]


@router.get("/analytics/demographics/geography", response_model=DimensionDistribution)
def demographics_geography(
    platform: str | None = None,
    repository: SocialRepository = Depends(get_repository),
) -> DimensionDistribution:
    service, signals = _demographic_signals(repository, platform)
    return service.aggregate(signals).dimensions["geography"]


@router.get("/analytics/demographics/language", response_model=DimensionDistribution)
def demographics_language(
    platform: str | None = None,
    repository: SocialRepository = Depends(get_repository),
) -> DimensionDistribution:
    service, signals = _demographic_signals(repository, platform)
    return service.aggregate(signals).dimensions["language"]


@router.get("/analytics/demographics/profession", response_model=DimensionDistribution)
def demographics_profession(
    platform: str | None = None,
    repository: SocialRepository = Depends(get_repository),
) -> DimensionDistribution:
    service, signals = _demographic_signals(repository, platform)
    return service.aggregate(signals).dimensions["profession"]


@router.get("/network/temporal")
def network_temporal(
    window: str = Query(default="1h", pattern="^(15m|1h|6h|24h)$"),
    count: int = Query(default=6, ge=1, le=48),
    platform: str | None = None,
    repository: SocialRepository = Depends(get_repository),
):
    from app.graph.schemas import TemporalNetworkResponse

    edges = repository.list_graph_edges(include_replay=False, platform=platform)
    snapshots, anchored_at = build_snapshots(edges, window=window, count=count)
    populated = [snapshot for snapshot in snapshots if snapshot.edges]
    if not populated:
        return TemporalNetworkResponse(
            window=window,
            window_count=len(snapshots),
            anchored_at=anchored_at,
            snapshots=snapshots,
            influence_changes=[],
            detail="No interaction relationships available for this window.",
        )
    detailed, _ = build_snapshots(edges, window=window, count=count, include_metrics=True)
    return TemporalNetworkResponse(
        window=window,
        window_count=len(snapshots),
        anchored_at=anchored_at,
        snapshots=snapshots,
        influence_changes=influence_changes(detailed),
        detail=f"Observed temporal snapshots over {len(populated)} populated windows.",
    )


@router.get("/network/influence")
def network_influence(
    metric: str = Query(default="pagerank", pattern="^(pagerank|betweenness_centrality|hub_score|authority_score)$"),
    limit: int = Query(default=20, ge=1, le=200),
    platform: str | None = None,
    repository: SocialRepository = Depends(get_repository),
):
    from app.graph.schemas import InfluenceEntry, InfluenceResponse

    edges = repository.list_graph_edges(include_replay=False, platform=platform)
    summary = calculate_network_metrics(GraphBuilder.build_graph(edges))
    ranked = sorted(summary.metrics, key=lambda item: getattr(item, metric), reverse=True)[:limit]
    window_start = min((edge.occurred_at for edge in edges), default=None)
    window_end = max((edge.occurred_at for edge in edges), default=None)
    return InfluenceResponse(
        metric=metric,
        window_start=window_start,
        window_end=window_end,
        nodes=summary.nodes,
        edges=summary.edges,
        items=[
            InfluenceEntry(
                node_id=item.node_id,
                community=item.community,
                in_degree_centrality=item.in_degree_centrality,
                out_degree_centrality=item.out_degree_centrality,
                betweenness_centrality=item.betweenness_centrality,
                closeness_centrality=item.closeness_centrality,
                pagerank=item.pagerank,
                hub_score=item.hub_score,
                authority_score=item.authority_score,
            )
            for item in ranked
        ],
        detail=(
            "Ranked by observed interaction structure; not a causal measure of real-world influence."
            if ranked else "Insufficient relationship data."
        ),
    )


@router.get("/network/communities")
def network_communities(
    limit: int | None = Query(default=None, ge=1, le=5000),
    platform: str | None = None,
    repository: SocialRepository = Depends(get_repository),
):
    from app.graph.audience import audience_dimensions, coverage
    from app.graph.schemas import CommunityListResponse

    edges = repository.list_graph_edges(
        include_replay=False, platform=platform, limit=limit,
        newest_first=limit is not None,
    )
    if not edges:
        return CommunityListResponse(detail="No interaction relationships available for this window.")
    communities = detect_communities(GraphBuilder.build_graph(edges))
    records = repository.graph_audience_records(set(communities))
    profiles = community_profiles(edges, communities)
    for profile in profiles:
        members = {node for node, community in communities.items() if community == profile.community_id}
        member_coverage = coverage(members, records)
        profile.stored_profiles = member_coverage.stored_profiles
        profile.referenced_only = member_coverage.referenced_only
        profile.audience = audience_dimensions(members, records)
    return CommunityListResponse(
        window_start=min(edge.occurred_at for edge in edges),
        window_end=max(edge.occurred_at for edge in edges),
        communities=profiles,
        coverage=coverage(set(communities), records),
        edge_sample_limit=limit,
        detail="Communities and audience cohorts use observed graph members; demographic categories require at least 3 known profiles per community.",
    )


def _cascade_events(repository: SocialRepository, platform: str | None) -> list[CascadeEvent]:
    records = repository.list_cascade_records(platform=platform)
    nlp_map = repository.nlp_map_for_events([record.event_id for record, _ in records])
    return [
        CascadeEvent(
            event_id=record.event_id,
            platform=record.platform,
            platform_post_id=record.platform_post_id,
            parent_platform_post_id=record.parent_platform_post_id,
            thread_root_id=record.thread_root_id,
            author_label=label,
            created_at=record.created_at,
            interaction_type=record.interaction_type,
            sentiment=nlp_map[record.event_id].sentiment_label if record.event_id in nlp_map else None,
            emotion=nlp_map[record.event_id].primary_emotion if record.event_id in nlp_map else None,
            is_ironic=nlp_map[record.event_id].is_ironic if record.event_id in nlp_map else None,
        )
        for record, label in records
    ]


@router.get("/network/cascades")
def network_cascades(
    platform: str | None = None,
    min_events: int = Query(default=2, ge=2, le=1000),
    limit: int = Query(default=50, ge=1, le=200),
    repository: SocialRepository = Depends(get_repository),
):
    from app.graph.schemas import CascadeListResponse, CascadeSummary

    cascades = [c for c in reconstruct_cascades(_cascade_events(repository, platform)) if c.event_count >= min_events][:limit]
    if not cascades:
        return CascadeListResponse(detail="No observable cascade reconstructed.")
    return CascadeListResponse(
        cascades=[
            CascadeSummary(
                cascade_id=cascade.cascade_id,
                platform=cascade.platform,
                root_platform_post_id=cascade.root_platform_post_id,
                event_count=cascade.event_count,
                depth=cascade.depth,
                width=cascade.width,
                duration_seconds=cascade.duration_seconds,
                participant_count=len(cascade.participants),
                community_count=0,
                interaction_types=sorted({event.interaction_type for event in cascade.events}),
                started_at=min(event.created_at for event in cascade.events),
                last_activity_at=max(event.created_at for event in cascade.events),
                provenance=cascade.provenance,
            )
            for cascade in cascades
        ],
        count=len(cascades),
        largest_cascade_id=cascades[0].cascade_id,
        max_depth=max(cascade.depth for cascade in cascades),
        detail=f"{len(cascades)} observed cascades reconstructed from stored relationships.",
    )


@router.get("/network/cascades/{cascade_id:path}")
def network_cascade_detail(
    cascade_id: str,
    platform: str | None = None,
    repository: SocialRepository = Depends(get_repository),
):
    from app.graph.schemas import CascadeDetail, PropagationStep

    cascades = reconstruct_cascades(_cascade_events(repository, platform))
    cascade = next((item for item in cascades if item.cascade_id == cascade_id), None)
    if cascade is None:
        raise HTTPException(status_code=404, detail="Cascade not found")
    edges = repository.list_graph_edges(include_replay=False, platform=cascade.platform)
    communities = detect_communities(GraphBuilder.build_graph(edges))
    counts, composition = sentiment_composition(cascade)
    steps = propagation_path(cascade, communities=communities)
    return CascadeDetail(
        cascade_id=cascade.cascade_id,
        platform=cascade.platform,
        root_platform_post_id=cascade.root_platform_post_id,
        event_count=cascade.event_count,
        depth=cascade.depth,
        width=cascade.width,
        duration_seconds=cascade.duration_seconds,
        participant_count=len(cascade.participants),
        communities=sorted({step["community"] for step in steps if step["community"] is not None}),
        provenance=cascade.provenance,
        sentiment_composition=composition,
        sentiment_counts=counts,
        propagation_path=[PropagationStep(**step) for step in steps],
        started_at=min(event.created_at for event in cascade.events),
        last_activity_at=max(event.created_at for event in cascade.events),
    )


@router.get("/network/summary", response_model=NetworkResponse)
def network_summary(
    platform: str | None = None,
    repository: SocialRepository = Depends(get_repository),
) -> NetworkResponse:
    graph = GraphBuilder.build_graph(
        repository.list_graph_edges(include_replay=False, platform=platform)
    )
    return NetworkResponse(summary=calculate_network_metrics(graph))


@router.get("/network/graph", response_model=NetworkGraphResponse)
def network_graph(
    limit: int = Query(default=500, ge=1, le=5000),
    platform: str | None = None,
    repository: SocialRepository = Depends(get_repository),
) -> NetworkGraphResponse:
    from app.graph.audience import public_profile

    edges = repository.list_graph_edges(
        include_replay=False,
        platform=platform,
        limit=limit,
        newest_first=True,
    )
    graph = GraphBuilder.build_graph(edges)
    summary = calculate_network_metrics(graph)
    records = repository.graph_audience_records(set(graph.nodes))
    for node in summary.metrics:
        node.profile = public_profile(records.get(node.node_id))
    return NetworkGraphResponse(
        nodes=summary.metrics,
        edges=[
            NetworkGraphEdge(
                event_id=edge.event_id,
                source=f"{edge.platform}:{edge.source_platform_user_id}",
                target=f"{edge.platform}:{edge.target_platform_user_id}",
                interaction_type=edge.interaction_type,
                weight=edge.weight,
                occurred_at=edge.occurred_at,
            )
            for edge in edges
        ],
        node_count=summary.nodes,
        edge_count=summary.edges,
    )
