from __future__ import annotations

import asyncio
import inspect
import logging
from collections.abc import Awaitable, Callable, Sequence
from datetime import UTC, datetime
from typing import Any

from telethon import events

from app.models.events import CanonicalEvent
from app.platforms.telegram.client import TelegramAPIError, TelegramClient
from app.platforms.telegram.mapper import TelegramEventMapper, require_public_channel
from app.platforms.telegram.models import TelegramStreamStats

logger = logging.getLogger(__name__)
EventCallback = Callable[[CanonicalEvent], None | Awaitable[None]]


def _value(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


class TelegramLiveStream:
    def __init__(
        self,
        telegram_client: TelegramClient,
        mapper: TelegramEventMapper | None = None,
        *,
        max_reconnect_attempts: int = 3,
    ):
        self.telegram_client = telegram_client
        self.mapper = mapper or TelegramEventMapper()
        self.max_reconnect_attempts = max_reconnect_attempts
        self.stats = TelegramStreamStats()
        self._stop_event: asyncio.Event | None = None
        self._callback: EventCallback | None = None

    async def run(
        self,
        channels: Sequence[str | int],
        on_event: EventCallback,
        *,
        stop_event: asyncio.Event | None = None,
    ) -> TelegramStreamStats:
        if not channels:
            raise ValueError("At least one Telegram public channel is required")
        self._stop_event = stop_event or asyncio.Event()
        self._callback = on_event
        reconnect_attempt = 0

        while not self._stop_event.is_set():
            raw_client = None
            handler_attached = False
            try:
                raw_client = await self.telegram_client.connect()
                target_entities = []
                for channel in channels:
                    entity = await self.telegram_client.execute(
                        "resolve_public_channel",
                        lambda channel=channel, client=raw_client: client.get_entity(
                            channel
                        ),
                    )
                    require_public_channel(entity)
                    target_entities.append(entity)

                raw_client.add_event_handler(
                    self.handle_update,
                    events.NewMessage(chats=target_entities),
                )
                handler_attached = True
                disconnected = asyncio.create_task(raw_client.run_until_disconnected())
                stopped = asyncio.create_task(self._stop_event.wait())
                done, pending = await asyncio.wait(
                    {disconnected, stopped}, return_when=asyncio.FIRST_COMPLETED
                )
                for task in pending:
                    task.cancel()
                await asyncio.gather(*pending, return_exceptions=True)
                if stopped in done and stopped.result():
                    await self.telegram_client.disconnect()
                    break
                exception = disconnected.exception()
                if exception is not None:
                    raise exception
                raise ConnectionError("Telegram update stream disconnected")
            except (TelegramAPIError, ConnectionError, OSError) as exc:
                if self._stop_event.is_set():
                    break
                reconnect_attempt += 1
                self.stats.reconnects += 1
                if reconnect_attempt > self.max_reconnect_attempts:
                    raise TelegramAPIError(
                        "Telegram live stream exceeded bounded reconnect attempts"
                    ) from exc
                delay = self.telegram_client._backoff(reconnect_attempt)
                logger.warning(
                    "Telegram live stream disconnected; reconnecting",
                    extra={
                        "service": "telegram-stream",
                        "platform": "telegram",
                        "operation": "reconnect",
                        "status": "RETRY",
                        "error": type(exc).__name__,
                        "duration_ms": round(delay * 1000, 2),
                    },
                )
                await self.telegram_client.sleeper(delay)
            finally:
                if raw_client is not None and handler_attached:
                    raw_client.remove_event_handler(self.handle_update)

        return self.stats.model_copy(deep=True)

    async def handle_update(self, update: Any) -> None:
        self.stats.received += 1
        message = _value(update, "message")
        try:
            chat = await self._event_value(update, "chat", "get_chat")
            require_public_channel(chat)
            sender = await self._event_value(update, "sender", "get_sender")
            reply_message = None
            reply_sender = None
            if self._reply_id(message) is not None:
                getter = _value(message, "get_reply_message")
                if callable(getter):
                    reply_message = await self.telegram_client.execute(
                        "live_reply_context", getter
                    )
                    reply_sender = await self._message_sender(reply_message)
            event = self.mapper.map_message(
                message,
                sender=sender,
                chat=chat,
                reply_message=reply_message,
                reply_sender=reply_sender,
                collected_at=datetime.now(UTC),
                mode="live",
            )
            if self._callback is None:
                raise RuntimeError("Telegram live callback is not configured")
            callback_result = self._callback(event)
            if inspect.isawaitable(callback_result):
                await callback_result
            self.stats.mapped += 1
        except Exception as exc:
            self.stats.rejected += 1
            logger.exception(
                "Rejected Telegram live update without stopping the stream",
                extra={
                    "service": "telegram-stream",
                    "platform": "telegram",
                    "event_id": str(_value(message, "id", "unknown")),
                    "operation": "normalize_live_update",
                    "status": "FAIL",
                    "error": str(exc),
                },
            )

    async def stop(self) -> None:
        if self._stop_event is not None:
            self._stop_event.set()
        await self.telegram_client.disconnect()

    async def _event_value(self, event: Any, attribute: str, getter_name: str) -> Any:
        value = _value(event, attribute)
        if value is not None:
            return value
        getter = _value(event, getter_name)
        if not callable(getter):
            return None
        return await self.telegram_client.execute(getter_name, getter)

    async def _message_sender(self, message: Any) -> Any:
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
