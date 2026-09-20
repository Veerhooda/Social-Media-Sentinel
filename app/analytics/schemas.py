from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TemporalPoint(BaseModel):
    window_start: datetime
    window_end: datetime
    event_count: int = Field(ge=0)
    positive_ratio: float = Field(ge=0, le=1)
    neutral_ratio: float = Field(ge=0, le=1)
    negative_ratio: float = Field(ge=0, le=1)
    emotion_distribution: dict[str, float]
    anxiety_average: float = Field(ge=0, le=1)
    excitement_average: float = Field(ge=0, le=1)
    irony_rate: float = Field(ge=0, le=1)
    stance_distribution: dict[str, float]


class TrendItem(BaseModel):
    topic: str
    volume: int = Field(ge=0)
    source: str

