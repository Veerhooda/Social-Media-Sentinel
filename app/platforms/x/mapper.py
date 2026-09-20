from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from app.models.events import (
    AuthorInfo,
    CanonicalEvent,
    ContentInfo,
    EngagementMetrics,
    InteractionType,
    MediaInfo,
    Platform,
    RelationshipInfo,
)

logger = logging.getLogger(__name__)


def _value(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _as_dict(obj: Any) -> dict[str, Any]:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    data = getattr(obj, "data", None)
    if isinstance(data, dict):
        return data
    return {
        key: value
        for key in dir(obj)
        if not key.startswith("_") and not callable(value := getattr(obj, key, None))
    }


def _timestamp(value: datetime | str | None) -> datetime:
    if value is None:
        raise ValueError("X post is missing created_at; request the created_at tweet field")
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("X post created_at must be timezone-aware")
    return value.astimezone(UTC)


class XEventMapper:
    def __init__(
        self,
        *,
        on_mapping_error: Callable[[Any, Exception], None] | None = None,
    ):
        self.on_mapping_error = on_mapping_error

    def map_response(
        self,
        response: Any,
        *,
        collected_at: datetime | None = None,
        mode: str = "recent_search",
        query: str | None = None,
    ) -> list[CanonicalEvent]:
        response_data = _value(response, "data")
        if response_data is None:
            posts: list[Any] = []
        elif isinstance(response_data, (list, tuple)):
            posts = list(response_data)
        else:
            # Tweepy search responses contain a list, while stream responses
            # contain one Tweet object in the same `data` field.
            posts = [response_data]
        includes = _value(response, "includes", {}) or {}
        users = {str(_value(user, "id")): user for user in _value(includes, "users", []) or []}
        referenced_posts = {
            str(_value(post, "id")): post for post in _value(includes, "tweets", []) or []
        }
        media = {str(_value(item, "media_key")): item for item in _value(includes, "media", []) or []}
        observed_at = collected_at or datetime.now(UTC)
        events: list[CanonicalEvent] = []
        for post in posts:
            try:
                events.append(
                    self.map_post(
                        post,
                        users=users,
                        referenced_posts=referenced_posts,
                        media=media,
                        collected_at=observed_at,
                        mode=mode,
                        query=query,
                    )
                )
            except (TypeError, ValueError) as exc:
                logger.error(
                    "Rejected malformed X post without stopping the response batch",
                    extra={
                        "service": "x-mapper",
                        "platform": "x",
                        "event_id": str(_value(post, "id", "unknown")),
                        "operation": "normalize",
                        "status": "FAIL",
                        "error": str(exc),
                    },
                )
                if self.on_mapping_error:
                    self.on_mapping_error(post, exc)
        return events

    def map_post(
        self,
        post: Any,
        *,
        users: dict[str, Any],
        referenced_posts: dict[str, Any],
        media: dict[str, Any],
        collected_at: datetime,
        mode: str,
        query: str | None,
    ) -> CanonicalEvent:
        post_id = str(_value(post, "id"))
        author_id = str(_value(post, "author_id"))
        author = users.get(author_id)
        if not post_id or post_id == "None":
            raise ValueError("X post is missing id")
        if not author_id or author_id == "None":
            raise ValueError("X post is missing author_id; request the author_id expansion")

        references = [_as_dict(item) for item in (_value(post, "referenced_tweets", []) or [])]
        ref_by_type = {str(item.get("type")): item for item in references}
        interaction_type = self._interaction_type(ref_by_type, post)
        primary_reference = self._primary_reference(ref_by_type)
        parent_id = str(primary_reference["id"]) if primary_reference else None

        parent_author_id = None
        if parent_id and parent_id in referenced_posts:
            parent_author = _value(referenced_posts[parent_id], "author_id")
            parent_author_id = str(parent_author) if parent_author is not None else None

        entities = _value(post, "entities", {}) or {}
        hashtag_values = [
            str(_value(tag, "tag", "")).lstrip("#")
            for tag in (_value(entities, "hashtags", []) or [])
            if _value(tag, "tag")
        ]
        mentions = [
            str(_value(item, "username", "")).lstrip("@")
            for item in (_value(entities, "mentions", []) or [])
            if _value(item, "username")
        ]
        mention_ids = [
            str(_value(item, "id"))
            for item in (_value(entities, "mentions", []) or [])
            if _value(item, "id") is not None
        ]
        attachments = _value(post, "attachments", {}) or {}
        media_items = [self._media(media[key]) for key in (_value(attachments, "media_keys", []) or []) if key in media]

        user_metrics = _value(author, "public_metrics", {}) or {}
        public_metrics = _value(post, "public_metrics", {}) or {}
        quote_ref = ref_by_type.get("quoted")
        repost_ref = ref_by_type.get("retweeted")
        reply_ref = ref_by_type.get("replied_to")

        return CanonicalEvent(
            platform=Platform.X,
            platform_post_id=post_id,
            parent_platform_post_id=parent_id,
            thread_root_id=str(_value(post, "conversation_id") or post_id),
            interaction_type=interaction_type,
            created_at=_timestamp(_value(post, "created_at")),
            collected_at=collected_at,
            author=AuthorInfo(
                platform_user_id=author_id,
                username=_value(author, "username"),
                display_name=_value(author, "name"),
                bio=_value(author, "description"),
                location_raw=_value(author, "location"),
                avatar_url=_value(author, "profile_image_url"),
                followers_count=int(_value(user_metrics, "followers_count", 0) or 0),
                following_count=int(_value(user_metrics, "following_count", 0) or 0),
                is_verified=_value(author, "verified"),
            ),
            content=ContentInfo(
                text=str(_value(post, "text", "")),
                language=_value(post, "lang"),
                hashtags=hashtag_values,
                mentions=mentions,
                media=media_items,
            ),
            relationships=RelationshipInfo(
                parent_author_id=parent_author_id if reply_ref else None,
                repost_of_author_id=parent_author_id if repost_ref else None,
                quote_of_event_id=str(quote_ref["id"]) if quote_ref else None,
                quote_of_author_id=parent_author_id if quote_ref else None,
            ),
            metrics=EngagementMetrics(
                likes=int(_value(public_metrics, "like_count", 0) or 0),
                shares=int(_value(public_metrics, "retweet_count", 0) or 0),
                comments=int(_value(public_metrics, "reply_count", 0) or 0),
                views=int(_value(public_metrics, "impression_count", 0) or 0),
                quotes=int(_value(public_metrics, "quote_count", 0) or 0),
                bookmarks=int(_value(public_metrics, "bookmark_count", 0) or 0),
            ),
            source_metadata={
                "raw_event_type": "x_post",
                "collection_mode": mode,
                "query": query,
                "conversation_id": str(_value(post, "conversation_id") or post_id),
                "mention_ids": mention_ids,
                "referenced_posts": references,
                "replay": False,
            },
        )

    @staticmethod
    def _interaction_type(ref_by_type: dict[str, dict[str, Any]], post: Any) -> InteractionType:
        if "replied_to" in ref_by_type:
            return InteractionType.REPLY
        if "retweeted" in ref_by_type:
            return InteractionType.REPOST
        if "quoted" in ref_by_type:
            return InteractionType.QUOTE
        entities = _value(post, "entities", {}) or {}
        if _value(entities, "mentions", []) or []:
            return InteractionType.MENTION
        return InteractionType.POST

    @staticmethod
    def _primary_reference(ref_by_type: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
        for name in ("replied_to", "retweeted", "quoted"):
            if name in ref_by_type:
                return ref_by_type[name]
        return None

    @staticmethod
    def _media(item: Any) -> MediaInfo:
        return MediaInfo(
            media_key=_value(item, "media_key"),
            media_type=str(_value(item, "type", "unknown")),
            url=_value(item, "url"),
            preview_url=_value(item, "preview_image_url"),
            alt_text=_value(item, "alt_text"),
        )
