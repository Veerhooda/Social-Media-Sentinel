from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AnalysisStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIPPED = "SKIPPED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class SignalStatus(StrEnum):
    EMERGING = "emerging"
    RISING = "rising"
    EXPLOSIVE = "explosive"
    SUSTAINED = "sustained"
    COOLING = "cooling"


class TrendDocument(BaseModel):
    event_id: UUID
    platform: str
    text: str = Field(min_length=1)
    created_at: datetime
    sentiment_label: str | None = None


class MicroBatch(BaseModel):
    window_start: datetime
    window_end: datetime
    documents: list[TrendDocument]

    @property
    def document_count(self) -> int:
        return len(self.documents)


class DiscoveredTopic(BaseModel):
    local_topic_id: int
    name: str
    keywords: list[str]
    document_ids: list[UUID]
    window_start: datetime
    window_end: datetime
    lineage_key: str | None = None
    match_score: float | None = Field(default=None, ge=-1, le=1)
    centroid: list[float] = Field(default_factory=list, exclude=True)


class BackendAnalysisResult(BaseModel):
    status: AnalysisStatus
    engine: str
    topics: list[DiscoveredTopic] = Field(default_factory=list)
    eligible_batches: int = 0
    matched_topics: int = 0
    detail: str | None = None


class TopicCatalogEntry(BaseModel):
    topic_id: int
    topic_key: str
    name: str
    keywords: list[str]


class TopicEvolutionPoint(BaseModel):
    window_start: datetime
    window_end: datetime
    volume: int = Field(ge=0)
    growth: float | None = None
    velocity: float | None = None
    acceleration: float | None = None
    status: str
    sentiment: dict[str, float] = Field(default_factory=dict)


class TopicSummary(BaseModel):
    topic_id: int | None = None
    topic: str
    keywords: list[str] = Field(default_factory=list)
    volume: int = Field(ge=0)
    growth: float | None = None
    velocity: float | None = None
    acceleration: float | None = None
    window_start: datetime | None = None
    window_end: datetime | None = None
    status: str
    sentiment: dict[str, float] = Field(default_factory=dict)
    source: str = "bertrend"


class TopicDetail(TopicSummary):
    model_name: str | None = None
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    evolution: list[TopicEvolutionPoint] = Field(default_factory=list)


class TopicListResponse(BaseModel):
    status: AnalysisStatus
    engine: str
    items: list[TopicSummary]
    detail: str | None = None


class TopicEvolutionResponse(BaseModel):
    status: AnalysisStatus
    topic_id: int
    topic: str
    items: list[TopicEvolutionPoint]
    detail: str | None = None


class TrendAnalyticsResponse(BaseModel):
    status: AnalysisStatus
    temporal_status: AnalysisStatus
    engine: str
    fallback: bool = False
    items: list[TopicSummary]
    detail: str | None = None


class TrendRunResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: AnalysisStatus
    temporal_status: AnalysisStatus
    engine: str
    documents: int = Field(ge=0)
    batches: int = Field(ge=0)
    eligible_batches: int = Field(ge=0)
    topics_discovered: int = Field(ge=0)
    topics_matched_across_windows: int = Field(ge=0)
    topics_persisted: int = Field(ge=0)
    measurements_persisted: int = Field(ge=0)
    detail: str | None = None
