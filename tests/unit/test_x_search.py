from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from types import SimpleNamespace

from app.core.config import Settings
from app.platforms.x.adapter import XAdapter
from app.platforms.x.client import XClient
from app.platforms.x.search import XRecentSearch


class FakeSearchClient:
    def __init__(self, pages):
        self.pages = list(pages)
        self.calls = []

    def search_recent_tweets(self, **kwargs):
        self.calls.append(kwargs)
        return self.pages.pop(0)


def response(payload, *, next_token=None):
    meta = dict(payload["meta"])
    if next_token:
        meta["next_token"] = next_token
    return SimpleNamespace(data=payload["data"], includes=payload["includes"], meta=meta)


def test_recent_search_follows_pagination_token(x_response_payload) -> None:
    page_two = deepcopy(x_response_payload)
    page_two["data"][0]["id"] = "2003"
    fake = FakeSearchClient([response(x_response_payload, next_token="next-1"), response(page_two)])
    client = XClient(Settings(), client=fake, sleeper=lambda _: None)

    result = XRecentSearch(client).search("#OpenData", max_results=10, max_pages=2)

    assert result.pages_fetched == 2
    assert [event.platform_post_id for event in result.events] == ["2002", "2003"]
    assert "next_token" not in fake.calls[0]
    assert fake.calls[1]["next_token"] == "next-1"
    assert "author_id" in fake.calls[0]["expansions"]


def test_recent_search_passes_source_time_bounds(x_response_payload) -> None:
    fake = FakeSearchClient([response(x_response_payload)])
    client = XClient(Settings(), client=fake)
    start = datetime(2026, 9, 20, 15, 0, tzinfo=UTC)
    end = datetime(2026, 9, 20, 15, 15, tzinfo=UTC)

    XRecentSearch(client).search(
        "ChatGPT lang:en",
        max_results=10,
        start_time=start,
        end_time=end,
    )

    assert fake.calls[0]["start_time"] == start
    assert fake.calls[0]["end_time"] == end


def test_recent_search_rejects_invalid_page_size() -> None:
    fake = FakeSearchClient([])
    client = XClient(Settings(), client=fake)
    try:
        XRecentSearch(client).search("query", max_results=9)
    except ValueError as exc:
        assert "between 10 and 100" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_health_check_is_skipped_without_credentials() -> None:
    settings = Settings(x_bearer_token=None)
    health = XAdapter(settings=settings, x_client=XClient(settings)).health_check()
    assert health.status == "SKIPPED"
    assert health.configured is False
