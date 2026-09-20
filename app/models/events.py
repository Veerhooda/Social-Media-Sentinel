from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Platform(StrEnum):
    X = "x"
    TELEGRAM = "telegram"
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    REDDIT = "reddit"


class InteractionType(StrEnum):
    POST = "post"
    REPLY = "reply"
    MENTION = "mention"
    REPOST = "repost"
    QUOTE = "quote"
    FORWARD = "forward"
    COMMENT = "comment"


class AuthorInfo(StrictModel):
    platform_user_id: str = Field(min_length=1, max_length=128)
    username: str | None = Field(default=None, max_length=128)
    display_name: str | None = Field(default=None, max_length=256)
    bio: str | None = None
    location_raw: str | None = Field(default=None, max_length=256)
    avatar_url: HttpUrl | None = None
    followers_count: int = Field(default=0, ge=0)
    following_count: int = Field(default=0, ge=0)
    is_verified: bool | None = None


class MediaInfo(StrictModel):
    media_key: str | None = Field(default=None, max_length=256)
    media_type: str = Field(min_length=1, max_length=32)
    url: HttpUrl | None = None
    preview_url: HttpUrl | None = None
    alt_text: str | None = None


class ContentInfo(StrictModel):
    text: str = ""
    language: str | None = Field(default=None, max_length=16)
    hashtags: list[str] = Field(default_factory=list)
    mentions: list[str] = Field(default_factory=list)
    media: list[MediaInfo] = Field(default_factory=list)

    @field_validator("hashtags", "mentions")
    @classmethod
    def unique_values(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(value for value in values if value))


class RelationshipInfo(StrictModel):
    parent_author_id: str | None = Field(default=None, max_length=128)
    repost_of_author_id: str | None = Field(default=None, max_length=128)
    quote_of_event_id: str | None = Field(default=None, max_length=128)
    quote_of_author_id: str | None = Field(default=None, max_length=128)
    forwarded_from_id: str | None = Field(default=None, max_length=128)


class EngagementMetrics(StrictModel):
    likes: int = Field(default=0, ge=0)
    shares: int = Field(default=0, ge=0)
    comments: int = Field(default=0, ge=0)
    views: int = Field(default=0, ge=0)
    quotes: int = Field(default=0, ge=0)
    bookmarks: int = Field(default=0, ge=0)


class CanonicalEvent(StrictModel):
    event_id: UUID = Field(default_factory=uuid4)
    platform: Platform
    platform_post_id: str = Field(min_length=1, max_length=128)
    parent_platform_post_id: str | None = Field(default=None, max_length=128)
    thread_root_id: str | None = Field(default=None, max_length=128)
    interaction_type: InteractionType
    created_at: datetime
    collected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    author: AuthorInfo
    content: ContentInfo
    relationships: RelationshipInfo = Field(default_factory=RelationshipInfo)
    metrics: EngagementMetrics = Field(default_factory=EngagementMetrics)
    source_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("created_at", "collected_at")
    @classmethod
    def require_aware_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        return value.astimezone(UTC)

