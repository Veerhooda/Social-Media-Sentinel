from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any, TypeVar

import requests
import tweepy

from app.core.config import Settings, get_settings

T = TypeVar("T")
logger = logging.getLogger(__name__)


class XAuthenticationError(RuntimeError):
    pass


class XAPIError(RuntimeError):
    pass


class XClient:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        client: Any | None = None,
        max_attempts: int = 3,
        sleeper: Callable[[float], None] = time.sleep,
    ):
        self.settings = settings or get_settings()
        self.max_attempts = max_attempts
        self.sleeper = sleeper
        if client is not None:
            self.client = client
        elif self.settings.x_bearer_token:
            self.client = tweepy.Client(
                bearer_token=self.settings.x_bearer_token,
                wait_on_rate_limit=False,
                return_type=tweepy.Response,
            )
        else:
            self.client = None

    @property
    def configured(self) -> bool:
        return self.client is not None

    def require_client(self) -> Any:
        if self.client is None:
            raise XAuthenticationError("X_BEARER_TOKEN is not configured")
        return self.client

    def execute(self, operation: str, call: Callable[[], T]) -> T:
        for attempt in range(1, self.max_attempts + 1):
            started = time.monotonic()
            try:
                result = call()
                logger.info(
                    "X API request completed",
                    extra={
                        "service": "x-client",
                        "platform": "x",
                        "operation": operation,
                        "duration_ms": round((time.monotonic() - started) * 1000, 2),
                        "status": "PASS",
                    },
                )
                return result
            except (tweepy.Unauthorized, tweepy.Forbidden) as exc:
                raise XAuthenticationError(f"X API rejected credentials/access: {exc}") from exc
            except tweepy.TooManyRequests as exc:
                if attempt == self.max_attempts:
                    raise XAPIError(f"X API rate limit remained active after {attempt} attempts") from exc
                delay = self._rate_limit_delay(exc, attempt)
                self._log_retry(operation, attempt, delay, exc)
                self.sleeper(delay)
            except (tweepy.TwitterServerError, requests.ConnectionError, requests.Timeout) as exc:
                if attempt == self.max_attempts:
                    raise XAPIError(f"X API transient failure after {attempt} attempts: {exc}") from exc
                delay = self._backoff(attempt)
                self._log_retry(operation, attempt, delay, exc)
                self.sleeper(delay)
            except tweepy.HTTPException as exc:
                response = getattr(exc, "response", None)
                status = getattr(response, "status_code", "unknown")
                raise XAPIError(
                    f"X API request failed with HTTP {status}: {exc}"
                ) from exc
        raise AssertionError("unreachable")

    @staticmethod
    def _backoff(attempt: int) -> float:
        return min(60.0, (2 ** (attempt - 1)) + random.uniform(0.0, 0.5))

    def _rate_limit_delay(self, exc: tweepy.TooManyRequests, attempt: int) -> float:
        response = getattr(exc, "response", None)
        headers = getattr(response, "headers", {}) or {}
        reset = headers.get("x-rate-limit-reset")
        retry_after = headers.get("retry-after")
        if retry_after:
            return min(60.0, max(0.0, float(retry_after)))
        if reset:
            try:
                return min(60.0, max(0.0, float(reset) - datetime.now(UTC).timestamp()))
            except ValueError:
                try:
                    parsed = parsedate_to_datetime(reset)
                    return min(60.0, max(0.0, parsed.timestamp() - datetime.now(UTC).timestamp()))
                except (TypeError, ValueError):
                    pass
        return self._backoff(attempt)

    @staticmethod
    def _log_retry(operation: str, attempt: int, delay: float, exc: Exception) -> None:
        logger.warning(
            "Retrying bounded X API request",
            extra={
                "service": "x-client",
                "platform": "x",
                "operation": operation,
                "status": "RETRY",
                "error": str(exc),
                "duration_ms": round(delay * 1000, 2),
            },
        )
