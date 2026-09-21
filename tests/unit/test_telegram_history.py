from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.platforms.telegram.adapter import TelegramAdapter
from app.platforms.telegram.client import TelegramClient


def channel() -> SimpleNamespace:
    return SimpleNamespace(
        id=777,
        title="Public Research",
        username="public_research",
        broadcast=True,
        megagroup=False,
    )


def message(
    message_id: int | None,
    minute: int,
    *,
    author_id: int = 1001,
    reply_to: int | None = None,
) -> SimpleNamespace:
    author = SimpleNamespace(
        id=author_id,
        username=f"author_{author_id}",
        first_name="Public",
        last_name="Author",
        verified=False,
    )
    return SimpleNamespace(
        id=message_id,
        chat_id=-100777,
        sender_id=author_id,
        sender=author,
        date=datetime(2026, 9, 20, 9, minute, tzinfo=UTC),
        raw_text=f"Public message {message_id} #research",
        reply_to_msg_id=reply_to,
        reply_to=(
            SimpleNamespace(reply_to_msg_id=reply_to, reply_to_top_id=None)
            if reply_to
            else None
        ),
        fwd_from=None,
        entities=[],
        media=None,
        forwards=0,
        views=10,
        replies=None,
        reactions=None,
        post_author=None,
    )


class FakeTelethonClient:
    def __init__(self, messages):
        self.messages = messages
        self.entity = channel()
        self.min_ids: list[int] = []
        self.connected = False
        self.disconnects = 0

    async def connect(self):
        self.connected = True

    async def is_user_authorized(self):
        return True

    async def disconnect(self):
        self.connected = False
        self.disconnects += 1

    async def get_entity(self, target):
        return self.entity

    def iter_messages(self, entity, *, limit, offset_date, min_id, reverse):
        self.min_ids.append(min_id)

        async def iterator():
            selected = [
                item
                for item in sorted(
                    self.messages,
                    key=lambda value: int(value.id or 0),
                    reverse=True,
                )
                if item.id is None or item.id > min_id
            ][:limit]
            for item in selected:
                yield item

        return iterator()

    async def get_messages(self, entity, *, ids):
        return [item for item in self.messages if item.id in ids]


@pytest.mark.asyncio
async def test_bounded_history_preserves_order_relationship_and_checkpoint() -> None:
    raw = FakeTelethonClient([message(2, 2, reply_to=1), message(1, 1, author_id=2002)])
    adapter = TelegramAdapter(telegram_client=TelegramClient(client=raw))

    first = await adapter.historical("public_research", max_messages=2)

    assert first.fetched_count == 2
    assert first.rejected_count == 0
    assert [event.platform_post_id for event in first.events] == [
        "-100777:1",
        "-100777:2",
    ]
    assert first.events[1].relationships.parent_author_id == "2002"
    assert first.checkpoint is not None
    assert first.checkpoint.last_message_id == 2
    assert raw.disconnects == 1

    raw.messages.append(message(3, 3))
    second = await adapter.historical(
        "public_research",
        max_messages=2,
        checkpoint=first.checkpoint,
    )
    assert [event.platform_post_id for event in second.events] == ["-100777:3"]
    assert raw.min_ids == [0, 2]


@pytest.mark.asyncio
async def test_history_applies_time_bounds_and_rejects_malformed_message() -> None:
    malformed = message(None, 4)
    raw = FakeTelethonClient([message(1, 1), message(2, 2), malformed])
    adapter = TelegramAdapter(telegram_client=TelegramClient(client=raw))

    result = await adapter.historical(
        "public_research",
        max_messages=3,
        start_time=datetime(2026, 9, 20, 9, 2, tzinfo=UTC),
        end_time=datetime(2026, 9, 20, 9, 5, tzinfo=UTC),
    )

    assert [event.platform_post_id for event in result.events] == ["-100777:2"]
    assert result.rejected_count == 1


@pytest.mark.asyncio
async def test_history_refuses_private_dialog() -> None:
    raw = FakeTelethonClient([])
    raw.entity = SimpleNamespace(
        id=7, username="person", broadcast=False, megagroup=False
    )
    adapter = TelegramAdapter(telegram_client=TelegramClient(client=raw))

    with pytest.raises(ValueError, match="public channel"):
        await adapter.historical("person", max_messages=1)


def test_history_requires_timezone_aware_bounds() -> None:
    raw = FakeTelethonClient([])
    adapter = TelegramAdapter(telegram_client=TelegramClient(client=raw))

    async def invoke() -> None:
        await adapter.historical(
            "public_research",
            start_time=datetime(2026, 9, 20, 9, 0, tzinfo=UTC).replace(tzinfo=None),
        )

    with pytest.raises(ValueError, match="timezone-aware"):
        import asyncio

        asyncio.run(invoke())
