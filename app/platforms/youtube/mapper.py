"""Map YouTube comment payloads into canonical events.

Top-level comments become ``comment`` events; replies become ``reply``
events carrying the parent comment ID and the parent author's platform ID
so the shared graph builder derives reply edges. No relationship is
invented: when a reply's parent author is unknown, only the parent post
reference is preserved.
"""
from __future__ import annotations

import re
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

from app.models.events import (
    AuthorInfo,
    CanonicalEvent,
    ContentInfo,
    EngagementMetrics,
    InteractionType,
    Platform,
    RelationshipInfo,
)

HASHTAG_PATTERN = re.compile(r"(?<!\w)#([\w_]+)", re.UNICODE)
MENTION_PATTERN = re.compile(r"(?<!\w)@([A-Za-z0-9_.\-]{1,64})")


def _int(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _timestamp(raw: Any) -> datetime:
    if not raw:
        raise ValueError("YouTube comment is missing its published timestamp")
    text = str(raw).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"unparseable YouTube timestamp {raw!r}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("YouTube timestamp must be timezone-aware")
    return parsed.astimezone(UTC)


def _author(snippet: dict[str, Any], comment_id: str) -> AuthorInfo:
    channel = snippet.get("authorChannelId") or {}
    channel_id = channel.get("value") if isinstance(channel, dict) else None
    fallback_id = f"comment-author:{sha256(comment_id.encode()).hexdigest()[:24]}"
    return AuthorInfo(
        # Display names are mutable and non-unique. A comment-scoped fallback
        # avoids merging unrelated people into one stored SocialUser.
        platform_user_id=str(channel_id or fallback_id),
        display_name=str(snippet.get("authorDisplayName") or "Unknown")[:256],
    )


def _content(text: str | None) -> ContentInfo:
    body = (text or "").strip()
    return ContentInfo(
        text=body,
        hashtags=HASHTAG_PATTERN.findall(body),
        mentions=MENTION_PATTERN.findall(body),
    )


def map_comment(
    snippet: dict[str, Any],
    comment_id: str,
    *,
    video_id: str,
    thread_root_id: str,
    parent_comment_id: str | None,
    parent_author_id: str | None,
    collected_at: datetime,
) -> CanonicalEvent:
    if not comment_id:
        raise ValueError("YouTube comment is missing its ID")
    is_reply = parent_comment_id is not None
    text = snippet.get("textOriginal") or snippet.get("textDisplay") or ""
    return CanonicalEvent(
        platform=Platform.YOUTUBE,
        platform_post_id=str(comment_id),
        parent_platform_post_id=str(parent_comment_id) if parent_comment_id else None,
        thread_root_id=str(thread_root_id),
        interaction_type=InteractionType.REPLY if is_reply else InteractionType.COMMENT,
        created_at=_timestamp(snippet.get("publishedAt")),
        collected_at=collected_at,
        author=_author(snippet, comment_id),
        content=_content(text if isinstance(text, str) else ""),
        relationships=RelationshipInfo(
            parent_author_id=str(parent_author_id) if parent_author_id else None,
        ),
        metrics=EngagementMetrics(likes=_int(snippet.get("likeCount"))),
        source_metadata={
            "video_id": video_id,
            "channel_id": snippet.get("channelId"),
            "raw_event_type": "youtube_comment_reply" if is_reply else "youtube_comment_thread",
            "updated_at": snippet.get("updatedAt"),
            "author_id_source": (
                "channel_id" if (snippet.get("authorChannelId") or {}).get("value")
                else "comment_scoped_fallback"
            ),
            # Textual @mentions on YouTube do not provide verified user IDs.
            "mention_relationships_verified": False,
            "replay": False,
        },
    )


def thread_root_and_replies(
    thread: dict[str, Any], *, video_id: str, collected_at: datetime
) -> tuple[CanonicalEvent, list[CanonicalEvent], list[dict[str, Any]], int]:
    """Split one commentThread resource into canonical top-level + inline replies."""
    snippet = thread.get("snippet") or {}
    top_detail = snippet.get("topLevelComment") or {}
    top_snippet = top_detail.get("snippet") or {}
    top_id = top_detail.get("id") or ""
    top_event = map_comment(
        top_snippet, top_id, video_id=video_id, thread_root_id=top_id,
        parent_comment_id=None, parent_author_id=None, collected_at=collected_at,
    )
    top_event = top_event.model_copy(
        update={"metrics": top_event.metrics.model_copy(update={"comments": _int(snippet.get("totalReplyCount"))})}
    )
    inline = ((thread.get("replies") or {}).get("comments")) or []
    events: list[CanonicalEvent] = []
    raw_replies: list[dict[str, Any]] = []
    for item in inline:
        if not isinstance(item, dict):
            continue
        item_snippet = item.get("snippet") or {}
        reply_id = item.get("id") or ""
        if not reply_id:
            continue
        raw_replies.append(item)
        events.append(
            map_comment(
                item_snippet, reply_id, video_id=video_id, thread_root_id=top_id,
                parent_comment_id=item_snippet.get("parentId") or top_id,
                parent_author_id=(
                    top_event.author.platform_user_id
                    if item_snippet.get("parentId", top_id) == top_id
                    and top_event.source_metadata["author_id_source"] == "channel_id"
                    else None
                ),
                collected_at=collected_at,
            )
        )
    total_replies = _int(snippet.get("totalReplyCount"))
    return top_event, events, raw_replies, total_replies
