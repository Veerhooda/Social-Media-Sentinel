"""Unit tests for YouTube canonical mapping (fixture-only, no network)."""
import json
from datetime import UTC
from pathlib import Path

import pytest

from app.models.events import InteractionType, Platform
from app.platforms.youtube.mapper import map_comment, thread_root_and_replies

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _threads():
    return json.loads((FIXTURES / "youtube_thread_response.json").read_text())["items"]


def test_top_level_comment_mapping() -> None:
    from datetime import datetime

    thread = _threads()[0]
    top, inline, raw, total = thread_root_and_replies(
        thread, video_id="video-abc", collected_at=datetime(2026, 9, 20, 12, tzinfo=UTC),
    )
    assert top.platform == Platform.YOUTUBE
    assert top.platform_post_id == "comment-top-1"
    assert top.interaction_type == InteractionType.COMMENT
    assert top.parent_platform_post_id is None
    assert top.thread_root_id == "comment-top-1"
    assert top.created_at == datetime(2026, 9, 18, 10, 0, tzinfo=UTC)
    assert top.author.platform_user_id == "UC_top1"
    assert top.author.display_name == "Commenter One"
    assert top.content.text == "Great analysis! #ai"
    assert top.content.hashtags == ["ai"]
    assert top.metrics.likes == 42
    assert top.source_metadata["video_id"] == "video-abc"
    assert len(inline) == 1 and total == 2
    reply = inline[0]
    assert reply.interaction_type == InteractionType.REPLY
    assert reply.parent_platform_post_id == "comment-top-1"
    assert reply.thread_root_id == "comment-top-1"
    assert reply.content.mentions == ["friend"]
    assert reply.created_at > top.created_at


def test_solo_comment_without_replies() -> None:
    from datetime import datetime

    thread = _threads()[1]
    top, inline, _, total = thread_root_and_replies(
        thread, video_id="video-abc", collected_at=datetime(2026, 9, 20, 12, tzinfo=UTC),
    )
    assert top.platform_post_id == "comment-top-2"
    assert inline == [] and total == 0
    # Display names are not stable user IDs; fallback is comment-scoped.
    assert top.author.platform_user_id.startswith("comment-author:")
    assert top.author.platform_user_id != top.author.display_name
    assert top.author.display_name == "Solo Viewer"


def test_missing_timestamp_rejected() -> None:
    from datetime import datetime

    with pytest.raises(ValueError, match="timestamp"):
        map_comment(
            {"textOriginal": "hi"}, "cid", video_id="v",
            thread_root_id="cid", parent_comment_id=None,
            parent_author_id=None, collected_at=datetime(2026, 9, 20, 12, tzinfo=UTC),
        )


def test_missing_comment_id_rejected() -> None:
    from datetime import datetime

    with pytest.raises(ValueError, match="ID"):
        map_comment(
            {"publishedAt": "2026-09-18T10:00:00Z"}, "", video_id="v",
            thread_root_id="x", parent_comment_id=None,
            parent_author_id=None, collected_at=datetime(2026, 9, 20, 12, tzinfo=UTC),
        )
