from datetime import UTC, datetime

from app.platforms.x.mapper import XEventMapper


def test_maps_x_response_to_canonical_event_and_preserves_timestamp(x_response_payload) -> None:
    collected = datetime(2026, 9, 20, 10, 15, 5, tzinfo=UTC)
    event = XEventMapper().map_response(x_response_payload, collected_at=collected)[0]

    assert event.platform == "x"
    assert event.platform_post_id == "2002"
    assert event.created_at == datetime(2026, 9, 20, 10, 15, tzinfo=UTC)
    assert event.collected_at == collected
    assert event.interaction_type == "reply"
    assert event.parent_platform_post_id == "2001"
    assert event.relationships.parent_author_id == "user-a"
    assert event.author.platform_user_id == "user-b"
    assert event.content.hashtags == ["OpenData"]
    assert event.content.mentions == ["origin"]
    assert event.source_metadata["mention_ids"] == ["user-a"]
    assert event.metrics.views == 120
    assert event.content.media[0].media_type == "photo"


def test_malformed_x_post_does_not_drop_valid_post(x_response_payload) -> None:
    failures = []
    malformed = {"id": "bad", "text": "missing author and timestamp"}
    payload = dict(x_response_payload)
    payload["data"] = [malformed, *x_response_payload["data"]]
    mapper = XEventMapper(on_mapping_error=lambda post, exc: failures.append((post, exc)))

    events = mapper.map_response(payload)

    assert [event.platform_post_id for event in events] == ["2002"]
    assert len(failures) == 1
    assert failures[0][0]["id"] == "bad"
