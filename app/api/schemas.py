from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.analytics.schemas import TemporalPoint
from app.graph.schemas import NetworkSummary
from app.models.events import CanonicalEvent
from app.trends.schemas import TrendAnalyticsResponse


class ComponentHealth(BaseModel):
    status: Literal["PASS", "FAIL", "SKIPPED", "UNAVAILABLE"]
    detail: str


class HealthResponse(BaseModel):
    status: Literal["PASS", "DEGRADED", "FAIL"]
    database: ComponentHealth
    x_api: ComponentHealth
    event_count: int = Field(ge=0)


class EventListResponse(BaseModel):
    items: list[CanonicalEvent]
    count: int = Field(ge=0)


class LiveEventsResponse(BaseModel):
    mode: Literal["live", "replay", "mixed", "idle"]
    label: str
    items: list[CanonicalEvent]


class TemporalSeriesResponse(BaseModel):
    rolling_1h: list[TemporalPoint]
    daily: list[TemporalPoint]


class NetworkResponse(BaseModel):
    summary: NetworkSummary


__all__ = [
    "ComponentHealth",
    "EventListResponse",
    "HealthResponse",
    "LiveEventsResponse",
    "NetworkResponse",
    "TemporalSeriesResponse",
    "TrendAnalyticsResponse",
]
