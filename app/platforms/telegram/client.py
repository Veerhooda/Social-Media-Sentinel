from __future__ import annotations

import asyncio
import inspect
import logging
import random
import time
from collections.abc import Awaitable, Callable
from typing import Any

from telethon import TelegramClient as TelethonClient
from telethon.errors import (
    AuthKeyError,
    FloodWaitError,
    RPCError,
    ServerError,
    TimedOutError,
    UnauthorizedError,
)
from telethon.sessions import StringSession

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class TelegramAuthenticationError(RuntimeError):
    pass


class TelegramAPIError(RuntimeError):
    pass


async def _await_result[T](value: T | Awaitable[T]) -> T:
    if inspect.isawaitable(value):
        return await value
    return value


class TelegramClient:
    """Credential/session and bounded-retry boundary around Telethon."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        client: Any | None = None,
        max_attempts: int = 3,
        sleeper: Callable[[float], Awaitable[None]] = asyncio.sleep,
        jitter: Callable[[], float] = random.random,
    ):
        self.settings = settings or get_settings()
        self.max_attempts = max_attempts
        self.sleeper = sleeper
        self.jitter = jitter
        if client is not None:
            self.client = client
        elif self._credentials_configured:
            self.client = TelethonClient(
                StringSession(self.settings.telegram_session_string),
                self.settings.telegram_api_id,
                self.settings.telegram_api_hash,
                auto_reconnect=True,
                connection_retries=max_attempts,
                request_retries=max_attempts,
                retry_delay=1,
                flood_sleep_threshold=0,
                receive_updates=True,
            )
        else:
            self.client = None

    @property
    def _credentials_configured(self) -> bool:
        return bool(
            self.settings.telegram_api_id
            and self.settings.telegram_api_hash
            and self.settings.telegram_session_string
        )

    @property
    def configured(self) -> bool:
        return self.client is not None

    def require_client(self) -> Any:
        if self.client is None:
            raise TelegramAuthenticationError(
                "TELEGRAM_API_ID, TELEGRAM_API_HASH, and TELEGRAM_SESSION_STRING are required"
            )
        return self.client

    async def connect(self) -> Any:
        client = self.require_client()
        await self.execute("connect", client.connect)
        authorized = await self.execute("authorization", client.is_user_authorized)
        if not authorized:
            await self.disconnect()
            raise TelegramAuthenticationError("Telegram session is not authorized")
        return client

    async def disconnect(self) -> None:
        if self.client is None:
            return
        try:
            await _await_result(self.client.disconnect())
        except (ConnectionError, OSError):
            logger.warning(
                "Telegram disconnect ended with a transport error",
                extra={
                    "service": "telegram-client",
                    "platform": "telegram",
                    "operation": "disconnect",
                    "status": "UNAVAILABLE",
                },
            )

    async def execute[T](
        self, operation: str, call: Callable[[], T | Awaitable[T]]
    ) -> T:
        for attempt in range(1, self.max_attempts + 1):
            started = time.monotonic()
            try:
                result = await _await_result(call())
                logger.info(
                    "Telegram operation completed",
                    extra={
                        "service": "telegram-client",
                        "platform": "telegram",
                        "operation": operation,
                        "duration_ms": round((time.monotonic() - started) * 1000, 2),
                        "status": "PASS",
                    },
                )
                return result
            except FloodWaitError as exc:
                if attempt == self.max_attempts:
                    raise TelegramAPIError(
                        f"Telegram FloodWait remained active after {attempt} attempts"
                    ) from exc
                delay = float(exc.seconds)
                self._log_retry(operation, attempt, delay, exc)
                await self.sleeper(delay)
            except (AuthKeyError, UnauthorizedError) as exc:
                raise TelegramAuthenticationError(
                    f"Telegram rejected the configured session: {exc}"
                ) from exc
            except (
                ServerError,
                TimedOutError,
                TimeoutError,
                ConnectionError,
                OSError,
            ) as exc:
                if attempt == self.max_attempts:
                    raise TelegramAPIError(
                        f"Telegram transient failure after {attempt} attempts: {exc}"
                    ) from exc
                delay = self._backoff(attempt)
                self._log_retry(operation, attempt, delay, exc)
                await self.sleeper(delay)
            except RPCError as exc:
                raise TelegramAPIError(f"Telegram RPC request failed: {exc}") from exc
        raise AssertionError("unreachable")

    def _backoff(self, attempt: int) -> float:
        return min(60.0, (2 ** (attempt - 1)) + (self.jitter() * 0.5))

    @staticmethod
    def _log_retry(operation: str, attempt: int, delay: float, exc: Exception) -> None:
        logger.warning(
            "Retrying bounded Telegram operation",
            extra={
                "service": "telegram-client",
                "platform": "telegram",
                "operation": operation,
                "status": "RETRY",
                "error": type(exc).__name__,
                "attempt": attempt,
                "duration_ms": round(delay * 1000, 2),
            },
        )
