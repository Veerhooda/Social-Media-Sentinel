"""Aggregate-first demographic schemas.

Individual inference stays inside the processing layer. The API and
dashboard only receive aggregate distributions with explicit unknown and
insufficient-data handling.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

DimensionStatus = Literal["AVAILABLE", "INSUFFICIENT_DATA", "UNAVAILABLE", "ERROR"]

AGE_BRACKETS: tuple[str, ...] = ("<=18", "19-29", "30-39", ">=40")

PROFESSIONAL_SECTORS: tuple[str, ...] = (
    "Technology",
    "Education",
    "Finance",
    "Healthcare",
    "Business",
    "Media",
    "Government",
    "Research",
    "Other",
    "Unknown",
)

UNKNOWN_LABEL = "Unknown"


class UserDemographicSignal(BaseModel):
    """Internal per-user inference. Never returned directly by the API."""

    user_id: UUID
    platform: str
    age_bracket: str | None = None
    age_confidence: float | None = None
    age_source: str = "unavailable"
    country: str | None = None
    region: str | None = None
    geography_confidence: float | None = None
    geography_source: str = "unknown"
    language: str | None = None
    language_confidence: float | None = None
    language_source: str = "unknown"
    professional_sector: str | None = None
    profession_confidence: float | None = None
    profession_source: str = "unknown"
    inference_source: str = "demographic-service-v1"


class AggregateSegment(BaseModel):
    label: str
    count: int = Field(ge=0)
    share: float = Field(ge=0.0, le=1.0)
    avg_confidence: float | None = None


class DimensionDistribution(BaseModel):
    dimension: Literal["age", "geography", "language", "profession"]
    status: DimensionStatus
    detail: str = ""
    total_subjects: int = Field(ge=0)
    unknown_count: int = Field(ge=0)
    segments: list[AggregateSegment] = Field(default_factory=list)
    updated_at: datetime | None = None


class DemographicsResponse(BaseModel):
    status: DimensionStatus
    detail: str = ""
    total_subjects: int = Field(ge=0)
    dimensions: dict[str, DimensionDistribution] = Field(default_factory=dict)
    updated_at: datetime | None = None


__all__ = [
    "AGE_BRACKETS",
    "PROFESSIONAL_SECTORS",
    "UNKNOWN_LABEL",
    "AggregateSegment",
    "UserDemographicSignal",
    "DimensionDistribution",
    "DimensionStatus",
    "DemographicsResponse",
]
