import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.platforms.telegram.client import TelegramClient
from app.platforms.telegram.stream import TelegramLiveStream


def channel() -> SimpleNamespace:
    return SimpleNamespace(
        id=777,
        title="Public Research",
        username="public_research",
        broadcast=True,
        megagroup=False,
    )


def live_message() -> SimpleNamespace:
    sender = SimpleNamespace(
        id=1001,
        username="live_author",
        first_name="Live",
        last_name="Author",
        verified=False,
    )
    return SimpleNamespace(
        id=50,
        chat_id=-100777,
        sender_id=1001,
        sender=sender,
        date=datetime(2026, 9, 20, 10, 0, tzinfo=UTC),
        raw_text="A genuinely shaped live update #telegram",
        reply_to_msg_id=None,
        reply_to=None,
        fwd_from=None,
        entities=[],
        media=None,
        forwards=0,
        views=2,
        replies=None,
        reactions=None,
        post_author=None,
    )


class FakeStreamClient:
    def __init__(self, stop_event: asyncio.Event):
        self.stop_event = stop_event
        self.run_count = 0
        self.handlers = []
        self.remove_count = 0
        self.disconnect_count = 0

    async def connect(self):
        return None

    async def is_user_authorized(self):
        return True

    async def disconnect(self):
        self.disconnect_count += 1

    async def get_entity(self, target):
        return channel()

    def add_event_handler(self, handler, event):
        self.handlers.append(handler)

    def remove_event_handler(self, handler):
        self.remove_count += 1

    async def run_until_disconnected(self):
        self.run_count += 1
        if self.run_count == 1:
            raise ConnectionError("controlled first disconnect")
        self.stop_event.set()
        await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_live_update_maps_and_calls_shared_pipeline_callback() -> None:
    wrapper = TelegramClient(client=object())
    stream = TelegramLiveStream(wrapper)
    received = []
    stream._callback = received.append
    update = SimpleNamespace(
        message=live_message(),
        chat=channel(),
        sender=live_message().sender,
    )

    await stream.handle_update(update)

    assert stream.stats.received == 1
    assert stream.stats.mapped == 1
    assert stream.stats.rejected == 0
    assert received[0].platform.value == "telegram"
    assert received[0].source_metadata["collection_mode"] == "live"


@pytest.mark.asyncio
async def test_stream_reconnects_once_and_stops_cleanly() -> None:
    stop_event = asyncio.Event()
    raw = FakeStreamClient(stop_event)
    sleeps: list[float] = []

    async def sleeper(delay: float) -> None:
        sleeps.append(delay)

    wrapper = TelegramClient(client=raw, sleeper=sleeper, jitter=lambda: 0)
    stream = TelegramLiveStream(wrapper, max_reconnect_attempts=2)

    stats = await stream.run(
        ["public_research"], lambda event: None, stop_event=stop_event
    )

    assert stats.reconnects == 1
    assert raw.run_count == 2
    assert raw.remove_count == 2
    assert raw.disconnect_count >= 1
    assert sleeps == [1.0]
