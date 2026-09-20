from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.analytics.schemas import TemporalPoint, TrendItem
from app.graph.schemas import NetworkSummary
from app.models.events import CanonicalEvent


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


class TrendResponse(BaseModel):
    engine: str
    items: list[TrendItem]


class NetworkResponse(BaseModel):
    summary: NetworkSummary
