from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.events import CanonicalEvent


class TelegramCheckpoint(BaseModel):
    channel: str
    last_message_id: int = Field(ge=0)
    last_created_at: datetime | None = None


class TelegramHistoryResult(BaseModel):
    events: list[CanonicalEvent]
    checkpoint: TelegramCheckpoint | None = None
    fetched_count: int = Field(ge=0)
    rejected_count: int = Field(ge=0)


class TelegramHealth(BaseModel):
    status: Literal["PASS", "FAIL", "SKIPPED", "UNAVAILABLE"]
    configured: bool
    live_checked: bool
    detail: str


class TelegramStreamStats(BaseModel):
    received: int = Field(default=0, ge=0)
    mapped: int = Field(default=0, ge=0)
    rejected: int = Field(default=0, ge=0)
    reconnects: int = Field(default=0, ge=0)
