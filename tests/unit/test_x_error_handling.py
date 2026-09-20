from types import SimpleNamespace

import pytest
import tweepy

from app.core.config import Settings
from app.platforms.x.client import XAPIError, XClient


def test_transient_x_server_error_uses_bounded_retry() -> None:
    calls = 0
    delays: list[float] = []
    response = SimpleNamespace(status_code=503, reason="Unavailable", json=lambda: {"errors": []})

    def operation():
        nonlocal calls
        calls += 1
        if calls == 1:
            raise tweepy.TwitterServerError(response)
        return "ok"

    client = XClient(Settings(), client=object(), max_attempts=2, sleeper=delays.append)
    assert client.execute("fixture", operation) == "ok"
    assert calls == 2
    assert len(delays) == 1
    assert 1 <= delays[0] <= 1.5


def test_x_rate_limit_respects_retry_after_with_bound() -> None:
    calls = 0
    delays: list[float] = []
    response = SimpleNamespace(
        status_code=429,
        reason="Too Many Requests",
        headers={"retry-after": "2"},
        json=lambda: {"errors": []},
    )

    def operation():
        nonlocal calls
        calls += 1
        if calls == 1:
            raise tweepy.TooManyRequests(response)
        return "ok"

    client = XClient(Settings(), client=object(), max_attempts=2, sleeper=delays.append)
    assert client.execute("fixture", operation) == "ok"
    assert delays == [2.0]


def test_non_retryable_x_http_error_is_explicit() -> None:
    response = SimpleNamespace(
        status_code=402,
        reason="Payment Required",
        headers={},
        json=lambda: {"detail": "credits depleted"},
    )
    client = XClient(Settings(), client=object(), max_attempts=3, sleeper=lambda _: None)

    with pytest.raises(XAPIError, match=r"(?s)HTTP 402.*credits depleted"):
        client.execute("fixture", lambda: (_ for _ in ()).throw(tweepy.HTTPException(response)))
