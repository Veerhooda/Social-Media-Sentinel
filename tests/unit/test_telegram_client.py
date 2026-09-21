import pytest
from telethon.errors import FloodWaitError

from app.core.config import Settings
from app.platforms.telegram.client import TelegramClient


def test_empty_telegram_api_id_placeholder_is_unconfigured() -> None:
    settings = Settings(
        telegram_api_id="",  # type: ignore[arg-type]
        telegram_api_hash="",
        telegram_session_string="",
    )
    assert settings.telegram_api_id is None
    assert TelegramClient(settings).configured is False


@pytest.mark.asyncio
async def test_flood_wait_uses_server_duration_then_retries() -> None:
    sleeps: list[float] = []
    attempts = 0

    async def sleeper(delay: float) -> None:
        sleeps.append(delay)

    async def operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise FloodWaitError(request=None, capture=2)
        return "ok"

    client = TelegramClient(client=object(), sleeper=sleeper)
    result = await client.execute("fixture", operation)

    assert result == "ok"
    assert attempts == 2
    assert sleeps == [2.0]


@pytest.mark.asyncio
async def test_transient_failure_has_bounded_backoff() -> None:
    sleeps: list[float] = []
    attempts = 0

    async def sleeper(delay: float) -> None:
        sleeps.append(delay)

    async def operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ConnectionError("controlled disconnect")
        return "connected"

    client = TelegramClient(
        client=object(), max_attempts=3, sleeper=sleeper, jitter=lambda: 0
    )
    assert await client.execute("fixture", operation) == "connected"
    assert sleeps == [1.0, 2.0]
