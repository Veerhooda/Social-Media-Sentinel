from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from telethon.tl.types import (
    Channel,
    ChatPhotoEmpty,
    Message,
    MessageReplyHeader,
    PeerChannel,
    PeerUser,
    User,
)

from app.platforms.telegram.mapper import (
    TelegramEventMapper,
    is_public_channel,
    require_public_channel,
)


def public_channel() -> SimpleNamespace:
    return SimpleNamespace(
        id=777,
        title="Public Research Channel",
        username="public_research",
        broadcast=True,
        megagroup=False,
    )


def sender(user_id: int, username: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=user_id,
        username=username,
        first_name=username.title(),
        last_name="Analyst",
        verified=False,
    )


def test_maps_reply_sender_text_media_metrics_and_source_timestamps() -> None:
    parent_sender = sender(2002, "parent_author")
    parent = SimpleNamespace(id=40, sender_id=2002, sender=parent_sender)
    message = SimpleNamespace(
        id=42,
        chat_id=-100777,
        sender_id=1001,
        sender=sender(1001, "telegram_author"),
        date=datetime(2026, 9, 20, 9, 30, tzinfo=UTC),
        raw_text="Research update #AI with @peer_team",
        reply_to_msg_id=40,
        reply_to=SimpleNamespace(reply_to_msg_id=40, reply_to_top_id=39),
        fwd_from=None,
        entities=[SimpleNamespace(user_id=3003)],
        media=SimpleNamespace(photo=SimpleNamespace(id=555)),
        photo=SimpleNamespace(id=555),
        document=None,
        forwards=7,
        views=450,
        replies=SimpleNamespace(replies=12),
        reactions=SimpleNamespace(
            results=[SimpleNamespace(count=5), SimpleNamespace(count=3)]
        ),
        post_author=None,
    )
    collected_at = datetime(2026, 9, 20, 9, 31, tzinfo=UTC)

    event = TelegramEventMapper().map_message(
        message,
        chat=public_channel(),
        reply_message=parent,
        reply_sender=parent_sender,
        collected_at=collected_at,
    )

    assert event.platform.value == "telegram"
    assert event.platform_post_id == "-100777:42"
    assert event.parent_platform_post_id == "-100777:40"
    assert event.thread_root_id == "-100777:39"
    assert event.created_at == message.date
    assert event.collected_at == collected_at
    assert event.author.platform_user_id == "1001"
    assert event.author.username == "telegram_author"
    assert event.content.hashtags == ["AI"]
    assert event.content.mentions == ["peer_team"]
    assert event.content.media[0].media_type == "photo"
    assert event.relationships.parent_author_id == "2002"
    assert event.source_metadata["mention_ids"] == ["3003"]
    assert event.metrics.likes == 8
    assert event.metrics.shares == 7
    assert event.metrics.comments == 12
    assert event.metrics.views == 450


def test_maps_forward_only_when_source_entity_is_available() -> None:
    message = SimpleNamespace(
        id=43,
        chat_id=-100777,
        sender_id=1001,
        sender=sender(1001, "telegram_author"),
        date=datetime(2026, 9, 20, 9, 35, tzinfo=UTC),
        raw_text="Forwarded research note",
        reply_to_msg_id=None,
        reply_to=None,
        fwd_from=SimpleNamespace(
            from_id=SimpleNamespace(channel_id=9009),
            saved_from_peer=None,
            from_name=None,
            channel_post=17,
        ),
        entities=[],
        media=None,
        forwards=1,
        views=20,
        replies=None,
        reactions=None,
        post_author=None,
    )

    event = TelegramEventMapper().map_message(message, chat=public_channel())

    assert event.interaction_type.value == "forward"
    assert event.relationships.forwarded_from_id == "9009"
    assert event.source_metadata["forwarded_channel_post_id"] == 17


def test_rejects_malformed_timestamps_and_private_dialog_targets() -> None:
    mapper = TelegramEventMapper()
    malformed = SimpleNamespace(
        id=44,
        chat_id=-100777,
        sender_id=1001,
        sender=sender(1001, "telegram_author"),
        date=datetime(2026, 9, 20, 9, 35, tzinfo=UTC).replace(tzinfo=None),
        raw_text="naive timestamp",
        reply_to_msg_id=None,
        reply_to=None,
        fwd_from=None,
        entities=[],
        media=None,
        forwards=None,
        views=None,
        replies=None,
        reactions=None,
        post_author=None,
    )
    with pytest.raises(ValueError, match="timezone-aware"):
        mapper.map_message(malformed, chat=public_channel())

    private_user = SimpleNamespace(
        id=9, username="private_user", broadcast=False, megagroup=False
    )
    assert is_public_channel(private_user) is False
    with pytest.raises(ValueError, match="public channel"):
        require_public_channel(private_user)


def test_maps_current_telethon_message_types_without_leaking_them_downstream() -> None:
    at = datetime(2026, 9, 20, 10, 0, tzinfo=UTC)
    chat = Channel(
        id=777,
        title="Public Research",
        photo=ChatPhotoEmpty(),
        date=at,
        broadcast=True,
        username="public_research",
    )
    author = User(id=1001, first_name="Telethon", username="telethon_author")
    message = Message(
        id=51,
        peer_id=PeerChannel(777),
        from_id=PeerUser(1001),
        date=at,
        message="Current Telethon object #verified",
        reply_to=MessageReplyHeader(reply_to_msg_id=50),
    )

    event = TelegramEventMapper().map_message(
        message,
        sender=author,
        chat=chat,
        collected_at=at,
    )

    assert event.platform_post_id == "-1000000000777:51"
    assert event.parent_platform_post_id == "-1000000000777:50"
    assert event.author.platform_user_id == "1001"
    assert event.content.hashtags == ["verified"]
    assert event.source_metadata["raw_event_type"] == "telegram_message"
