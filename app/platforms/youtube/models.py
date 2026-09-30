from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class YouTubeHealth(BaseModel):
    status: Literal["PASS", "FAIL", "SKIPPED", "UNAVAILABLE"]
    configured: bool = False
    live_checked: bool = False
    detail: str = ""


class YouTubeCheckpoint(BaseModel):
    video_id: str
    page_token: str | None = None
    thread_offset: int = Field(default=0, ge=0)
    comment_offset: int = Field(default=0, ge=0)
    reply_page_token: str | None = None
    reply_offset: int = Field(default=0, ge=0)
    collected_count: int = Field(default=0, ge=0)


class YouTubeCommentResult(BaseModel):
    video_id: str
    exhausted: bool = False
    comments_collected: int = Field(default=0, ge=0)
    replies_collected: int = Field(default=0, ge=0)
    duplicates_skipped: int = Field(default=0, ge=0)
    pages_fetched: int = Field(default=0, ge=0)
    api_calls: int = Field(default=0, ge=0)
    next_checkpoint: YouTubeCheckpoint
    incomplete_threads: int = Field(default=0, ge=0)
    rejected_count: int = Field(default=0, ge=0)
    detail: str = ""


class YouTubePollStats(BaseModel):
    video_id: str
    comments_collected: int = Field(default=0, ge=0)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    detail: str = ""
