from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from telethon import utils

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

HASHTAG_PATTERN = re.compile(r"(?<!\w)#([\w_]+)", re.UNICODE)
MENTION_PATTERN = re.compile(r"(?<!\w)@([A-Za-z0-9_]{1,32})")


def _value(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _timestamp(value: datetime | None) -> datetime:
    if value is None:
        raise ValueError("Telegram message is missing its source timestamp")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Telegram message timestamp must be timezone-aware")
    return value.astimezone(UTC)


def _peer_id(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (str, int)):
        return str(value)
    if isinstance(value, dict):
        for key in ("user_id", "channel_id", "chat_id", "id"):
            candidate = value.get(key)
            if candidate is not None:
                return str(candidate)
        return None
    try:
        return str(utils.get_peer_id(value))
    except (TypeError, ValueError):
        for key in ("user_id", "channel_id", "chat_id", "id"):
            candidate = getattr(value, key, None)
            if candidate is not None:
                return str(candidate)
    return None


def _public_username(entity: Any) -> str | None:
    username = _value(entity, "username")
    if username:
        return str(username)
    for candidate in _value(entity, "usernames", []) or []:
        if _value(candidate, "active", True) and _value(candidate, "username"):
            return str(_value(candidate, "username"))
    return None


def is_public_channel(entity: Any) -> bool:
    """Accept public broadcast channels and public supergroups, never user dialogs."""

    channel_kind = bool(
        _value(entity, "broadcast", False) or _value(entity, "megagroup", False)
    )
    return channel_kind and bool(_public_username(entity))


def require_public_channel(entity: Any) -> None:
    if not is_public_channel(entity):
        raise ValueError(
            "Telegram target must be a public channel or public supergroup with a username"
        )


class TelegramEventMapper:
    def map_message(
        self,
        message: Any,
        *,
        sender: Any | None = None,
        chat: Any | None = None,
        reply_message: Any | None = None,
        reply_sender: Any | None = None,
        collected_at: datetime | None = None,
        mode: str = "history",
    ) -> CanonicalEvent:
        message_id = _value(message, "id")
        if message_id is None:
            raise ValueError("Telegram message is missing id")
        if _value(message, "action") is not None:
            raise ValueError("Telegram service events are not canonical content messages")

        chat = chat or _value(message, "chat")
        chat_id = _peer_id(_value(message, "chat_id")) or _peer_id(chat)
        if chat_id is None:
            raise ValueError("Telegram message is missing channel/source id")

        sender = sender or _value(message, "sender")
        author_id = (
            _peer_id(_value(message, "sender_id")) or _peer_id(sender) or chat_id
        )
        if author_id is None:
            raise ValueError("Telegram message is missing sender metadata")

        created_at = _timestamp(_value(message, "date"))
        observed_at = collected_at or datetime.now(UTC)
        if observed_at.tzinfo is None or observed_at.utcoffset() is None:
            raise ValueError("Telegram collected_at must be timezone-aware")
        observed_at = observed_at.astimezone(UTC)

        platform_post_id = self._post_id(chat_id, message_id)
        reply_id = _value(message, "reply_to_msg_id")
        reply_header = _value(message, "reply_to")
        if reply_id is None:
            reply_id = _value(reply_header, "reply_to_msg_id")
        top_id = _value(reply_header, "reply_to_top_id")
        parent_post_id = (
            self._post_id(chat_id, reply_id) if reply_id is not None else None
        )
        thread_root_id = self._post_id(chat_id, top_id or reply_id or message_id)

        forward_header = _value(message, "fwd_from")
        forwarded_from = _peer_id(_value(forward_header, "from_id"))
        if forwarded_from is None:
            forwarded_from = _peer_id(_value(forward_header, "saved_from_peer"))

        parent_author_id = None
        if reply_id is not None:
            reply_sender = reply_sender or _value(reply_message, "sender")
            parent_author_id = _peer_id(_value(reply_message, "sender_id")) or _peer_id(
                reply_sender
            )

        text = str(_value(message, "raw_text") or _value(message, "message") or "")
        hashtags = [match.group(1) for match in HASHTAG_PATTERN.finditer(text)]
        mentions = [match.group(1) for match in MENTION_PATTERN.finditer(text)]
        mention_ids = self._mention_ids(_value(message, "entities", []) or [])
        media = self._media(message)

        if reply_id is not None:
            interaction = InteractionType.REPLY
        elif forward_header is not None:
            interaction = InteractionType.FORWARD
        elif mentions:
            interaction = InteractionType.MENTION
        else:
            interaction = InteractionType.POST

        reactions = _value(message, "reactions")
        likes = sum(
            int(_value(item, "count", 0) or 0)
            for item in (_value(reactions, "results", []) or [])
        )
        replies = _value(message, "replies")

        username = _value(sender, "username") or (
            _public_username(chat) if author_id == chat_id else None
        )
        first_name = _value(sender, "first_name")
        last_name = _value(sender, "last_name")
        display_name = (
            " ".join(str(item) for item in (first_name, last_name) if item)
            or _value(sender, "title")
            or _value(chat, "title")
        )

        follower_source = sender or chat if author_id == chat_id else sender
        return CanonicalEvent(
            platform=Platform.TELEGRAM,
            platform_post_id=platform_post_id,
            parent_platform_post_id=parent_post_id,
            thread_root_id=thread_root_id,
            interaction_type=interaction,
            created_at=created_at,
            collected_at=observed_at,
            author=AuthorInfo(
                platform_user_id=author_id,
                username=str(username) if username else None,
                display_name=str(display_name) if display_name else None,
                followers_count=int(
                    _value(follower_source, "participants_count", 0) or 0
                ),
                is_verified=_value(sender, "verified"),
            ),
            content=ContentInfo(
                text=text,
                language=None,
                hashtags=hashtags,
                mentions=mentions,
                media=media,
            ),
            relationships=RelationshipInfo(
                parent_author_id=parent_author_id,
                forwarded_from_id=forwarded_from,
            ),
            metrics=EngagementMetrics(
                likes=likes,
                shares=int(_value(message, "forwards", 0) or 0),
                comments=int(_value(replies, "replies", 0) or 0),
                views=int(_value(message, "views", 0) or 0),
            ),
            source_metadata={
                "raw_event_type": "telegram_message",
                "collection_mode": mode,
                "channel_id": chat_id,
                "channel_username": _public_username(chat),
                "channel_title": _value(chat, "title"),
                "message_id": str(message_id),
                "post_author": _value(message, "post_author"),
                "mention_ids": mention_ids,
                "forwarded_from_name": _value(forward_header, "from_name"),
                "forwarded_channel_post_id": _value(forward_header, "channel_post"),
                "replay": False,
            },
        )

    @staticmethod
    def _post_id(chat_id: str, message_id: Any) -> str:
        return f"{chat_id}:{message_id}"

    @staticmethod
    def _mention_ids(entities: list[Any]) -> list[str]:
        values = [
            str(user_id)
            for entity in entities
            if (user_id := _value(entity, "user_id")) is not None
        ]
        return list(dict.fromkeys(values))

    @staticmethod
    def _media(message: Any) -> list[MediaInfo]:
        media = _value(message, "media")
        if media is None:
            return []
        photo = _value(message, "photo") or _value(media, "photo")
        document = _value(message, "document") or _value(media, "document")
        if photo is not None:
            return [
                MediaInfo(
                    media_key=f"telegram:{_value(photo, 'id', 'photo')}",
                    media_type="photo",
                )
            ]
        if document is not None:
            mime_type = str(_value(document, "mime_type", "application/octet-stream"))
            if mime_type.startswith("video/"):
                media_type = "video"
            elif mime_type.startswith("audio/"):
                media_type = "audio"
            else:
                media_type = "document"
            return [
                MediaInfo(
                    media_key=f"telegram:{_value(document, 'id', 'document')}",
                    media_type=media_type,
                )
            ]
        kind = type(media).__name__.removeprefix("MessageMedia").lower() or "unknown"
        if kind == "empty":
            return []
        return [MediaInfo(media_key=None, media_type=kind[:32])]
