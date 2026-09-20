from datetime import UTC, datetime, timedelta

from app.models.events import AuthorInfo, CanonicalEvent, ContentInfo


def event(post_id: str, at: datetime) -> CanonicalEvent:
    return CanonicalEvent(
        platform="x",
        platform_post_id=post_id,
        interaction_type="post",
        created_at=at,
        collected_at=at + timedelta(seconds=1),
        author=AuthorInfo(platform_user_id="same-user", username="fixture"),
        content=ContentInfo(text=post_id),
    )


def test_postgres_insert_retrieve_deduplicate_and_chronological_query(repository) -> None:
    later = event("later", datetime(2026, 9, 20, 11, 0, tzinfo=UTC))
    earlier = event("earlier", datetime(2026, 9, 20, 10, 0, tzinfo=UTC))

    assert repository.insert_event(later).created is True
    assert repository.insert_event(earlier).created is True
    duplicate = repository.insert_event(earlier)

    assert duplicate.created is False
    assert repository.count_events() == 2
    assert [item.platform_post_id for item in repository.list_events()] == ["earlier", "later"]
    assert repository.get_event(earlier.event_id).created_at == earlier.created_at

