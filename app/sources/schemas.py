from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SourcePlatform(StrEnum):
    X = "x"
    TELEGRAM = "telegram"
    YOUTUBE = "youtube"


_YT_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_YT_URL = re.compile(r"(?:v=|youtu\.be/|/shorts/|/live/|/embed/)([A-Za-z0-9_-]{11})")
_TG_URL = re.compile(r"^(?:https?://)?t\.me/(?:s/)?([A-Za-z0-9_]{4,64})/?$")


def normalise_target(platform: SourcePlatform, raw: str) -> str:
    value = raw.strip()
    if platform is SourcePlatform.YOUTUBE:
        if _YT_ID.fullmatch(value):
            return value
        match = _YT_URL.search(value)
        if match:
            return match.group(1)
        raise ValueError("Enter a YouTube video URL or 11-character video id")
    if platform is SourcePlatform.TELEGRAM:
        match = _TG_URL.match(value)
        value = match.group(1) if match else value.removeprefix("@")
        if not re.fullmatch(r"[A-Za-z0-9_]{4,64}", value):
            raise ValueError("Enter a public channel username, @handle or t.me link")
        return value
    if not 1 <= len(value) <= 512:
        raise ValueError("X query must be 1-512 characters")
    return value


class SourceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    platform: SourcePlatform
    target: str = Field(min_length=1, max_length=600)
    label: str | None = Field(default=None, max_length=256)

    @model_validator(mode="after")
    def clean(self) -> SourceCreate:
        self.target = normalise_target(self.platform, self.target)
        return self


class SourceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool | None = None
    label: str | None = Field(default=None, max_length=256)


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    source_id: UUID
    platform: SourcePlatform
    target: str
    label: str | None
    enabled: bool
    origin: str = "database"
    last_run_at: datetime | None
    last_status: str | None
    last_detail: str | None
    last_fetched: int
    last_stored: int
    total_stored: int
    created_at: datetime | None


class PlatformCollector(BaseModel):
    platform: SourcePlatform
    credentials_configured: bool
    credential_detail: str
    job_name: str
    interval_seconds: float
    sources: list[SourceOut]


class SourcesOverview(BaseModel):
    scheduler_enabled: bool
    scheduler_running: bool
    platforms: list[PlatformCollector]
