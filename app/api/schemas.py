from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.analytics.schemas import TemporalPoint
from app.graph.schemas import NetworkSummary, NodeMetrics
from app.models.events import CanonicalEvent
from app.nlp.schemas import NLPResult
from app.scheduler.schemas import SchedulerStatus
from app.trends.schemas import TrendAnalyticsResponse


class ComponentHealth(BaseModel):
    status: Literal["PASS", "FAIL", "SKIPPED", "UNAVAILABLE"]
    detail: str


class PlatformDataSummary(BaseModel):
    platform: str
    event_count: int = Field(ge=0)
    real_event_count: int = Field(ge=0)
    replay_event_count: int = Field(ge=0)
    latest_created_at: datetime | None = None
    latest_collected_at: datetime | None = None

    @field_validator("latest_created_at", "latest_collected_at")
    @classmethod
    def normalize_utc(cls, value: datetime | None) -> datetime | None:
        return value.astimezone(UTC) if value is not None else None


class HealthResponse(BaseModel):
    status: Literal["PASS", "DEGRADED", "FAIL"]
    database: ComponentHealth
    x_api: ComponentHealth
    telegram_api: ComponentHealth
    youtube_api: ComponentHealth
    scheduler: ComponentHealth
    analytics: ComponentHealth
    event_count: int = Field(ge=0)
    real_event_count: int = Field(ge=0)
    replay_event_count: int = Field(ge=0)
    updated_at: datetime
    platforms: list[PlatformDataSummary]


class EventListResponse(BaseModel):
    items: list[CanonicalEvent]
    count: int = Field(ge=0)
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1)


class EnrichedEvent(BaseModel):
    event: CanonicalEvent
    analysis: NLPResult | None = None


class EnrichedEventListResponse(BaseModel):
    items: list[EnrichedEvent]
    count: int = Field(ge=0)
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1)


class LiveEventsResponse(BaseModel):
    mode: Literal["live", "replay", "mixed", "idle"]
    label: str
    items: list[CanonicalEvent]


class TemporalSeriesResponse(BaseModel):
    rolling_1h: list[TemporalPoint]
    daily: list[TemporalPoint]


class NetworkResponse(BaseModel):
    summary: NetworkSummary


class NetworkGraphEdge(BaseModel):
    event_id: UUID
    source: str
    target: str
    interaction_type: str
    weight: float
    occurred_at: datetime


class NetworkGraphResponse(BaseModel):
    nodes: list[NodeMetrics]
    edges: list[NetworkGraphEdge]
    node_count: int = Field(ge=0)
    edge_count: int = Field(ge=0)


__all__ = [
    "ComponentHealth",
    "EnrichedEvent",
    "EnrichedEventListResponse",
    "EventListResponse",
    "HealthResponse",
    "LiveEventsResponse",
    "NetworkResponse",
    "NetworkGraphResponse",
    "PlatformDataSummary",
    "TemporalSeriesResponse",
    "TrendAnalyticsResponse",
    "SchedulerStatus",
]
