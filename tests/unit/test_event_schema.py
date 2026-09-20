from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.models.events import AuthorInfo, CanonicalEvent, ContentInfo


def make_event(**overrides) -> CanonicalEvent:
    payload = {
        "platform": "x",
        "platform_post_id": "fixture-1",
        "interaction_type": "post",
        "created_at": datetime(2026, 9, 20, 12, 0, tzinfo=UTC),
        "collected_at": datetime(2026, 9, 20, 12, 1, tzinfo=UTC),
        "author": AuthorInfo(platform_user_id="user-1"),
        "content": ContentInfo(text="fixture"),
    }
    payload.update(overrides)
    return CanonicalEvent(**payload)


def test_event_requires_timezone_aware_timestamps() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        make_event(created_at=datetime(2026, 9, 20, 12, 0))


def test_event_normalizes_source_timestamp_to_utc() -> None:
    offset = timezone(timedelta(hours=5, minutes=30))
    event = make_event(created_at=datetime(2026, 9, 20, 17, 30, tzinfo=offset))
    assert event.created_at == datetime(2026, 9, 20, 12, 0, tzinfo=UTC)


def test_event_rejects_negative_engagement() -> None:
    with pytest.raises(ValidationError):
        make_event(metrics={"likes": -1})

