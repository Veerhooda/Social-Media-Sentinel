from datetime import UTC, datetime, timedelta

from app.analytics.temporal import aggregate_daily, aggregate_rolling
from app.models.events import AuthorInfo, CanonicalEvent, ContentInfo


def event(at: datetime, post_id: str) -> CanonicalEvent:
    return CanonicalEvent(
        platform="x",
        platform_post_id=post_id,
        interaction_type="post",
        created_at=at,
        collected_at=at + timedelta(seconds=2),
        author=AuthorInfo(platform_user_id=f"user-{post_id}"),
        content=ContentInfo(text="fixture"),
    )


def test_rolling_hour_and_daily_aggregation(fake_nlp_service) -> None:
    start = datetime(2026, 9, 20, 10, 2, tzinfo=UTC)
    events = [event(start, "1"), event(start + timedelta(minutes=20), "2")]
    records = [(item, fake_nlp_service.analyze(item)) for item in events]

    rolling = aggregate_rolling(records)
    daily = aggregate_daily(records)

    assert rolling[-1].event_count == 2
    assert rolling[-1].positive_ratio == 1.0
    assert rolling[-1].anxiety_average == 0.2
    assert rolling[-1].excitement_average == 0.7
    assert daily[0].event_count == 2

