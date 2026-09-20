from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, Field

from app.models.events import CanonicalEvent

X_TWEET_FIELDS: list[str] = [
    "id",
    "text",
    "author_id",
    "created_at",
    "conversation_id",
    "lang",
    "public_metrics",
    "referenced_tweets",
    "entities",
    "attachments",
]
X_EXPANSIONS: list[str] = [
    "author_id",
    "referenced_tweets.id",
    "referenced_tweets.id.author_id",
    "attachments.media_keys",
]
X_USER_FIELDS: list[str] = [
    "id",
    "username",
    "name",
    "description",
    "location",
    "public_metrics",
    "profile_image_url",
    "verified",
]
X_MEDIA_FIELDS: list[str] = ["media_key", "type", "url", "preview_image_url", "alt_text"]


class XSearchPage(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    events: list[CanonicalEvent]
    next_token: str | None = None
    result_count: int = Field(ge=0)


class XSearchResult(BaseModel):
    events: list[CanonicalEvent]
    pages_fetched: int = Field(ge=0)
    newest_id: str | None = None
    oldest_id: str | None = None


class XHealth(BaseModel):
    status: str
    configured: bool
    live_checked: bool
    detail: str


def listify(value: Sequence[object] | None) -> list[object]:
    return list(value or [])

