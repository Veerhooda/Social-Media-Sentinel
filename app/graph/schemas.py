from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EdgeRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    event_id: UUID
    platform: str
    source_platform_user_id: str
    target_platform_user_id: str
    interaction_type: str
    weight: float = Field(gt=0)
    occurred_at: datetime


class NodeMetrics(BaseModel):
    node_id: str
    in_degree_centrality: float
    out_degree_centrality: float
    betweenness_centrality: float
    closeness_centrality: float
    pagerank: float
    hub_score: float
    authority_score: float
    community: int | None = None


class NetworkSummary(BaseModel):
    nodes: int
    edges: int
    density: float
    communities: int
    metrics: list[NodeMetrics]
    interpretation: str = (
        "These structural metrics describe collected interactions; they are not causal measures of real-world influence."
    )



class TemporalSnapshot(BaseModel):
    window_start: datetime
    window_end: datetime
    label: str
    nodes: int = Field(ge=0)
    edges: int = Field(ge=0)
    density: float = 0.0
    communities: int = Field(ge=0)
    summary: NetworkSummary | None = None


class InfluenceDelta(BaseModel):
    node_id: str
    metric: str
    first_value: float
    last_value: float
    change: float
    direction: str
    windows_measured: int = Field(ge=1)


class TemporalNetworkResponse(BaseModel):
    window: str
    window_count: int = Field(ge=0)
    anchored_at: datetime | None = None
    snapshots: list[TemporalSnapshot] = Field(default_factory=list)
    influence_changes: list[InfluenceDelta] = Field(default_factory=list)
    detail: str = ""


class InfluenceEntry(BaseModel):
    node_id: str
    community: int | None = None
    in_degree_centrality: float
    out_degree_centrality: float
    betweenness_centrality: float
    closeness_centrality: float
    pagerank: float
    hub_score: float
    authority_score: float


class InfluenceResponse(BaseModel):
    metric: str
    window_start: datetime | None = None
    window_end: datetime | None = None
    nodes: int = Field(ge=0)
    edges: int = Field(ge=0)
    items: list[InfluenceEntry] = Field(default_factory=list)
    detail: str = ""


class CommunityProfile(BaseModel):
    community_id: int
    size: int = Field(ge=0)
    interaction_volume: int = Field(ge=0)
    dominant_interaction_types: list[str] = Field(default_factory=list)
    interaction_type_counts: dict[str, int] = Field(default_factory=dict)
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None


class CommunityListResponse(BaseModel):
    window_start: datetime | None = None
    window_end: datetime | None = None
    communities: list[CommunityProfile] = Field(default_factory=list)
    detail: str = ""


class CascadeSummary(BaseModel):
    cascade_id: str
    platform: str
    root_platform_post_id: str
    event_count: int = Field(ge=0)
    depth: int = Field(ge=0)
    width: int = Field(ge=0)
    duration_seconds: float | None = None
    participant_count: int = Field(ge=0)
    community_count: int = Field(ge=0)
    interaction_types: list[str] = Field(default_factory=list)
    started_at: datetime | None = None
    last_activity_at: datetime | None = None
    provenance: str = "observed"


class PropagationStep(BaseModel):
    depth: int = Field(ge=0)
    node_id: str
    event_id: UUID
    platform_post_id: str
    interaction_type: str
    occurred_at: datetime
    community: int | None = None
    sentiment: str | None = None
    emotion: str | None = None
    is_ironic: bool | None = None


class CascadeDetail(BaseModel):
    cascade_id: str
    platform: str
    root_platform_post_id: str
    event_count: int = Field(ge=0)
    depth: int = Field(ge=0)
    width: int = Field(ge=0)
    duration_seconds: float | None = None
    participant_count: int = Field(ge=0)
    communities: list[int] = Field(default_factory=list)
    provenance: str = "observed"
    topic_status: str = "unavailable"
    topic_detail: str = (
        "Per-event topic assignments are not persisted; topic-specific cascade analysis is unavailable."
    )
    sentiment_composition: dict[str, float] = Field(default_factory=dict)
    sentiment_counts: dict[str, int] = Field(default_factory=dict)
    propagation_path: list[PropagationStep] = Field(default_factory=list)
    started_at: datetime | None = None
    last_activity_at: datetime | None = None


class CascadeListResponse(BaseModel):
    cascades: list[CascadeSummary] = Field(default_factory=list)
    count: int = Field(ge=0)
    largest_cascade_id: str | None = None
    max_depth: int = Field(ge=0)
    detail: str = ""
