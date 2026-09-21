from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from app.platforms.telegram.client import TelegramAPIError, TelegramClient
from app.platforms.telegram.mapper import TelegramEventMapper, require_public_channel
from app.platforms.telegram.models import TelegramCheckpoint, TelegramHistoryResult

logger = logging.getLogger(__name__)


def _value(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _aware(value: datetime | None, name: str) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(UTC)


class TelegramHistory:
    def __init__(
        self,
        telegram_client: TelegramClient,
        mapper: TelegramEventMapper | None = None,
    ):
        self.telegram_client = telegram_client
        self.mapper = mapper or TelegramEventMapper()

    async def fetch(
        self,
        channel: str | int,
        *,
        max_messages: int = 100,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        checkpoint: TelegramCheckpoint | None = None,
        collected_at: datetime | None = None,
    ) -> TelegramHistoryResult:
        if not 1 <= max_messages <= 1000:
            raise ValueError("Telegram history max_messages must be between 1 and 1000")
        start_time = _aware(start_time, "start_time")
        end_time = _aware(end_time, "end_time")
        if start_time and end_time and start_time >= end_time:
            raise ValueError("start_time must be before end_time")
        if checkpoint and checkpoint.channel != str(channel):
            raise ValueError("Telegram checkpoint belongs to a different channel")

        raw_client = self.telegram_client.require_client()
        entity = await self.telegram_client.execute(
            "resolve_public_channel", lambda: raw_client.get_entity(channel)
        )
        require_public_channel(entity)

        async def collect_page() -> list[Any]:
            iterator = raw_client.iter_messages(
                entity,
                limit=max_messages,
                offset_date=end_time,
                min_id=checkpoint.last_message_id if checkpoint else 0,
                reverse=False,
            )
            return [message async for message in iterator]

        messages = await self.telegram_client.execute("history", collect_page)
        message_by_id = {
            int(message_id): message
            for message in messages
            if (message_id := _value(message, "id")) is not None
        }
        missing_parent_ids = sorted(
            {
                int(reply_id)
                for message in messages
                if (reply_id := self._reply_id(message)) is not None
                and int(reply_id) not in message_by_id
            }
        )
        if missing_parent_ids:
            parent_messages = await self.telegram_client.execute(
                "reply_context",
                lambda: raw_client.get_messages(entity, ids=missing_parent_ids),
            )
            if not isinstance(parent_messages, (list, tuple)):
                parent_messages = [parent_messages]
            for parent in parent_messages:
                parent_id = _value(parent, "id")
                if parent is not None and parent_id is not None:
                    message_by_id[int(parent_id)] = parent

        observed_at = collected_at or datetime.now(UTC)
        events = []
        rejected = 0
        for message in messages:
            created_at = _value(message, "date")
            if start_time and (
                created_at is None or _aware(created_at, "message.date") < start_time
            ):
                continue
            if end_time and (
                created_at is None or _aware(created_at, "message.date") >= end_time
            ):
                continue
            try:
                sender = await self._sender(message)
                reply_id = self._reply_id(message)
                reply_message = (
                    message_by_id.get(int(reply_id)) if reply_id is not None else None
                )
                reply_sender = (
                    await self._sender(reply_message)
                    if reply_message is not None
                    else None
                )
                events.append(
                    self.mapper.map_message(
                        message,
                        sender=sender,
                        chat=entity,
                        reply_message=reply_message,
                        reply_sender=reply_sender,
                        collected_at=observed_at,
                        mode="history",
                    )
                )
            except (TelegramAPIError, TypeError, ValueError) as exc:
                rejected += 1
                logger.error(
                    "Rejected malformed Telegram message without stopping history retrieval",
                    extra={
                        "service": "telegram-history",
                        "platform": "telegram",
                        "event_id": str(_value(message, "id", "unknown")),
                        "operation": "normalize",
                        "status": "FAIL",
                        "error": str(exc),
                    },
                )

        events.sort(key=lambda item: (item.created_at, item.platform_post_id))
        newest_message = max(
            messages,
            key=lambda item: int(_value(item, "id", 0) or 0),
            default=None,
        )
        next_checkpoint = checkpoint
        if newest_message is not None:
            next_checkpoint = TelegramCheckpoint(
                channel=str(channel),
                last_message_id=int(_value(newest_message, "id")),
                last_created_at=_aware(_value(newest_message, "date"), "message.date"),
            )
        return TelegramHistoryResult(
            events=events,
            checkpoint=next_checkpoint,
            fetched_count=len(messages),
            rejected_count=rejected,
        )

    async def _sender(self, message: Any | None) -> Any | None:
        if message is None:
            return None
        sender = _value(message, "sender")
        if sender is not None:
            return sender
        getter = _value(message, "get_sender")
        if callable(getter):
            return await self.telegram_client.execute("sender_metadata", getter)
        return None

    @staticmethod
    def _reply_id(message: Any) -> int | None:
        direct = _value(message, "reply_to_msg_id")
        if direct is not None:
            return int(direct)
        nested = _value(_value(message, "reply_to"), "reply_to_msg_id")
        return int(nested) if nested is not None else None
