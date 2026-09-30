"""Unit tests for bounded pagination, replies, dedup, errors (no network)."""
import json
from copy import deepcopy
from pathlib import Path

import pytest

from app.core.config import Settings
from app.platforms.youtube.adapter import YouTubeAdapter
from app.platforms.youtube.client import (
    YouTubeAPIError,
    YouTubeClient,
    YouTubeNotConfiguredError,
    YouTubeQuotaError,
)
from app.platforms.youtube.comments import YouTubeComments
from app.platforms.youtube.models import YouTubeCheckpoint

FIXTURES = Path(__file__).parent.parent / "fixtures"
THREADS = json.loads((FIXTURES / "youtube_thread_response.json").read_text())
REPLIES = json.loads((FIXTURES / "youtube_comments_response.json").read_text())


class FakeService:
    """Mimics googleapiclient's chained resource().list().execute() calls."""

    def __init__(self, *, threads_pages, replies_pages=None, error=None):
        self.threads_pages = list(threads_pages)
        self.replies_pages = list(replies_pages or [])
        self.error = error
        self.thread_calls = 0
        self.reply_calls = 0
        self._mode = None
        self._kwargs = {}
        self.requests = []

    def commentThreads(self):  # noqa: N802
        self._mode = "threads"
        return self

    def comments(self):  # noqa: N802
        self._mode = "replies"
        return self

    def list(self, **kwargs):
        self._kwargs = kwargs
        self.requests.append((self._mode, kwargs))
        return self

    def execute(self):
        if self.error is not None:
            raise self.error
        if self._mode == "threads":
            self.thread_calls += 1
            return self.threads_pages[min(self.thread_calls - 1, len(self.threads_pages) - 1)]
        self.reply_calls += 1
        return self.replies_pages[min(self.reply_calls - 1, len(self.replies_pages) - 1)]


def _client(service):
    return YouTubeClient(settings=None, service=service)


def test_pagination_bounded_and_replies_completed() -> None:
    page1 = dict(THREADS)
    service = FakeService(threads_pages=[page1, {"items": []}], replies_pages=[REPLIES])
    service_with_key = _client(service)
    service_with_key.settings = type("S", (), {"youtube_api_key": "key"})()
    events, result = YouTubeComments(service_with_key).fetch("video-abc", max_results=10, max_pages=2)
    ids = [e.platform_post_id for e in events]
    assert ids == ["comment-top-1", "comment-reply-1", "comment-reply-2", "comment-top-2"]
    assert result.replies_collected == 2
    assert result.comments_collected == 2
    assert result.pages_fetched == 2
    assert result.next_checkpoint.page_token is None
    assert result.exhausted
    assert service.thread_calls == 2 and service.reply_calls == 1


def test_max_results_bounds_collection() -> None:
    service = FakeService(threads_pages=[THREADS], replies_pages=[REPLIES])
    client = _client(service)
    client.settings = type("S", (), {"youtube_api_key": "key"})()
    events, _ = YouTubeComments(client).fetch("video-abc", max_results=2, max_pages=5)
    assert [e.platform_post_id for e in events] == ["comment-top-1", "comment-reply-1"]


def test_duplicates_skipped_within_run() -> None:
    service = FakeService(threads_pages=[THREADS], replies_pages=[{"items": []}])
    client = _client(service)
    client.settings = type("S", (), {"youtube_api_key": "key"})()
    first, _ = YouTubeComments(client).fetch("video-abc", max_results=10, max_pages=1)
    assert len(first) == 3  # top-1, reply-1, top-2 (reply-2 absent from empty page)


def test_comments_disabled_yields_empty_result() -> None:
    class DisabledError(Exception):
        def __init__(self):
            self.resp = type("R", (), {"status": 403, "reason": "forbidden"})()
            self.content = b'{"error": {"errors": [{"reason": "commentsDisabled"}]}}'

    service = FakeService(threads_pages=[THREADS], error=DisabledError())
    client = _client(service)
    client.settings = type("S", (), {"youtube_api_key": "key"})()
    events, result = YouTubeComments(client).fetch("video-abc")
    assert events == []
    assert "disabled" in result.detail


def test_quota_error_classified_without_retry() -> None:
    class QuotaError(Exception):
        def __init__(self):
            self.resp = type("R", (), {"status": 403, "reason": "forbidden"})()
            self.content = b'{"error": {"errors": [{"reason": "quotaExceeded"}]}}'

    service = FakeService(threads_pages=[THREADS], error=QuotaError())
    client = _client(service)
    client.settings = type("S", (), {"youtube_api_key": "key"})()
    try:
        YouTubeComments(client).fetch("video-abc")
    except YouTubeQuotaError:
        pass
    else:
        raise AssertionError("expected YouTubeQuotaError")


def test_unconfigured_adapter_reports_skipped() -> None:
    from app.core.config import Settings

    adapter = YouTubeAdapter(settings=Settings(youtube_api_key=None))
    health = adapter.configuration_health()
    assert health.status == "SKIPPED" and not health.configured
    try:
        adapter.collect("video-abc")
    except (YouTubeNotConfiguredError, YouTubeAPIError):
        pass
    else:
        raise AssertionError("expected a configuration error")


def test_malformed_thread_skipped_safely() -> None:
    service = FakeService(threads_pages=[{"items": [{"kind": "youtube#commentThread"}]}])
    client = _client(service)
    client.settings = type("S", (), {"youtube_api_key": "key"})()
    events, result = YouTubeComments(client).fetch("video-abc", max_results=5, max_pages=1)
    assert events == []
    assert result.rejected_count == 1


def test_reply_relationship_uses_known_parent_channel_id() -> None:
    service = FakeService(threads_pages=[THREADS], replies_pages=[REPLIES])
    client = _client(service)
    events, _ = YouTubeComments(client).fetch("video-abc", max_pages=1)
    by_id = {event.platform_post_id: event for event in events}
    assert by_id["comment-reply-1"].relationships.parent_author_id == "UC_top1"
    assert by_id["comment-reply-2"].relationships.parent_author_id == "UC_top1"
    assert by_id["comment-top-1"].metrics.comments == 2


def test_checkpoint_resumes_within_a_partially_processed_thread() -> None:
    service = FakeService(threads_pages=[THREADS], replies_pages=[REPLIES])
    client = _client(service)
    first, first_result = YouTubeComments(client).fetch("video-abc", max_results=2, max_pages=1)
    checkpoint = first_result.next_checkpoint
    assert [event.platform_post_id for event in first] == ["comment-top-1", "comment-reply-1"]
    assert (checkpoint.page_token, checkpoint.thread_offset, checkpoint.comment_offset) == (None, 0, 2)
    assert service.reply_calls == 0
    second, second_result = YouTubeComments(client).fetch(
        "video-abc", max_results=3, max_pages=1, checkpoint=checkpoint
    )
    assert [event.platform_post_id for event in second] == ["comment-reply-2", "comment-top-2"]
    assert service.reply_calls == 1
    assert second_result.next_checkpoint.collected_count == 4
    assert "pageToken" not in service.requests[0][1]


def test_repeated_page_token_stops_after_one_request() -> None:
    service = FakeService(
        threads_pages=[{**THREADS, "nextPageToken": "repeat"}], replies_pages=[REPLIES]
    )
    client = _client(service)
    with pytest.raises(YouTubeAPIError, match="repeated a page token"):
        YouTubeComments(client).fetch("video-abc", max_results=10, max_pages=3)
    assert service.thread_calls == 2


def test_api_call_budget_resumes_before_unfetched_replies() -> None:
    service = FakeService(threads_pages=[THREADS], replies_pages=[REPLIES])
    client = _client(service)
    first, first_result = YouTubeComments(client).fetch(
        "video-abc", max_results=10, max_pages=2, max_api_calls=1
    )
    assert [event.platform_post_id for event in first] == [
        "comment-top-1", "comment-reply-1"
    ]
    assert first_result.api_calls == 1
    assert not first_result.exhausted
    assert first_result.incomplete_threads == 1
    assert first_result.next_checkpoint.thread_offset == 0
    assert first_result.next_checkpoint.comment_offset == 2
    assert service.thread_calls == 1 and service.reply_calls == 0

    second, second_result = YouTubeComments(client).fetch(
        "video-abc", max_results=10, max_pages=2, max_api_calls=2,
        checkpoint=first_result.next_checkpoint,
    )
    assert [event.platform_post_id for event in second] == [
        "comment-reply-2", "comment-top-2"
    ]
    assert second_result.api_calls == 2
    assert second_result.next_checkpoint.collected_count == 4
    assert service.thread_calls == 2 and service.reply_calls == 1


def test_api_call_budget_resumes_across_reply_pages() -> None:
    reply_2 = REPLIES["items"][0]
    page_1 = {"items": [THREADS["items"][0]["replies"]["comments"][0]], "nextPageToken": "reply-next"}
    page_2 = {"items": [reply_2]}
    service = FakeService(threads_pages=[THREADS], replies_pages=[page_1, page_2])
    client = _client(service)
    first, first_result = YouTubeComments(client).fetch(
        "video-abc", max_results=10, max_pages=2, max_api_calls=2
    )
    assert [event.platform_post_id for event in first] == [
        "comment-top-1", "comment-reply-1"
    ]
    assert first_result.api_calls == 2
    assert first_result.next_checkpoint.reply_page_token == "reply-next"
    assert first_result.incomplete_threads == 1
    assert service.thread_calls + service.reply_calls == 2

    second, second_result = YouTubeComments(client).fetch(
        "video-abc", max_results=10, max_pages=2, max_api_calls=2,
        checkpoint=first_result.next_checkpoint,
    )
    assert [event.platform_post_id for event in second] == [
        "comment-reply-2", "comment-top-2"
    ]
    assert second_result.api_calls == 2
    assert second_result.next_checkpoint.collected_count == 4
    assert service.thread_calls + service.reply_calls == 4


def test_event_limit_resumes_within_a_reply_page() -> None:
    threads = deepcopy(THREADS)
    threads["items"][0]["snippet"]["totalReplyCount"] = 3
    reply_2 = REPLIES["items"][0]
    reply_3 = deepcopy(reply_2)
    reply_3["id"] = "comment-reply-3"
    replies = {"items": [reply_2, reply_3]}
    service = FakeService(threads_pages=[threads], replies_pages=[replies])
    client = _client(service)
    first, first_result = YouTubeComments(client).fetch(
        "video-abc", max_results=3, max_pages=1
    )
    assert [event.platform_post_id for event in first] == [
        "comment-top-1", "comment-reply-1", "comment-reply-2"
    ]
    assert first_result.next_checkpoint.reply_offset == 1

    second, second_result = YouTubeComments(client).fetch(
        "video-abc", max_results=10, max_pages=1,
        checkpoint=first_result.next_checkpoint,
    )
    assert [event.platform_post_id for event in second] == [
        "comment-reply-3", "comment-top-2"
    ]
    assert second_result.next_checkpoint.collected_count == 5


def test_checkpoint_cannot_cross_video_ids() -> None:
    service = FakeService(threads_pages=[THREADS])
    client = _client(service)
    with pytest.raises(ValueError, match="different video"):
        YouTubeComments(client).fetch("video-abc", checkpoint=YouTubeCheckpoint(video_id="other"))
    assert service.thread_calls == 0


def test_poll_once_dispatches_to_caller_and_never_claims_storage() -> None:
    service = FakeService(threads_pages=[{"items": [THREADS["items"][1]]}])
    adapter = YouTubeAdapter(
        settings=Settings(youtube_api_key="fixture", youtube_video_id="video-abc"),
        youtube_client=_client(service),
    )
    received = []
    stats = adapter.poll_once(received.append)
    assert stats.comments_collected == len(received) == 1
    assert "dispatched to caller" in stats.detail
