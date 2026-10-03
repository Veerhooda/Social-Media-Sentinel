from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from app.core.config import Settings, get_settings
from app.platforms.telegram.client import (
    TelegramAPIError,
    TelegramAuthenticationError,
    TelegramClient,
)
from app.platforms.telegram.history import TelegramHistory
from app.platforms.telegram.mapper import TelegramEventMapper
from app.platforms.telegram.models import (
    TelegramCheckpoint,
    TelegramHealth,
    TelegramHistoryResult,
    TelegramStreamStats,
)
from app.platforms.telegram.stream import EventCallback, TelegramLiveStream


class TelegramAdapter:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        telegram_client: TelegramClient | None = None,
        mapper: TelegramEventMapper | None = None,
    ):
        self.settings = settings or get_settings()
        self.mapper = mapper or TelegramEventMapper()
        self.telegram_client = telegram_client or TelegramClient(self.settings)
        self.history_service = TelegramHistory(self.telegram_client, self.mapper)

    async def historical(
        self,
        channel: str | int,
        *,
        max_messages: int = 100,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        checkpoint: TelegramCheckpoint | None = None,
        peer: tuple[int, int] | None = None,
    ) -> TelegramHistoryResult:
        await self.telegram_client.connect()
        try:
            input_peer = None
            if peer is not None:
                from telethon.tl.types import InputPeerChannel

                input_peer = InputPeerChannel(channel_id=peer[0], access_hash=peer[1])
            return await self.history_service.fetch(
                channel,
                max_messages=max_messages,
                start_time=start_time,
                end_time=end_time,
                checkpoint=checkpoint,
                peer=input_peer,
            )
        finally:
            await self.telegram_client.disconnect()

    async def stream(
        self,
        channels: Sequence[str | int],
        on_event: EventCallback,
        *,
        stop_event=None,
        max_reconnect_attempts: int = 3,
    ) -> TelegramStreamStats:
        stream = TelegramLiveStream(
            self.telegram_client,
            self.mapper,
            max_reconnect_attempts=max_reconnect_attempts,
        )
        return await stream.run(channels, on_event, stop_event=stop_event)

    def configuration_health(self) -> TelegramHealth:
        if not self.telegram_client.configured:
            return TelegramHealth(
                status="SKIPPED",
                configured=False,
                live_checked=False,
                detail=(
                    "TELEGRAM_API_ID, TELEGRAM_API_HASH, and "
                    "TELEGRAM_SESSION_STRING are not fully configured"
                ),
            )
        return TelegramHealth(
            status="PASS",
            configured=True,
            live_checked=False,
            detail="Telegram client configured; live request not requested",
        )

    async def health_check(self, *, live: bool = False) -> TelegramHealth:
        configured = self.configuration_health()
        if not live or not configured.configured:
            return configured
        try:
            raw_client = await self.telegram_client.connect()
            await self.telegram_client.execute("health_check", raw_client.get_me)
        except TelegramAuthenticationError as exc:
            return TelegramHealth(
                status="FAIL",
                configured=True,
                live_checked=True,
                detail=str(exc),
            )
        except TelegramAPIError as exc:
            return TelegramHealth(
                status="UNAVAILABLE",
                configured=True,
                live_checked=True,
                detail=str(exc),
            )
        finally:
            await self.telegram_client.disconnect()
        return TelegramHealth(
            status="PASS",
            configured=True,
            live_checked=True,
            detail="Telegram API request succeeded",
        )
