from __future__ import annotations

import logging
from collections.abc import Callable
from threading import current_thread
from typing import Any

import tweepy

from app.models.events import CanonicalEvent
from app.platforms.x.mapper import XEventMapper
from app.platforms.x.models import (
    X_EXPANSIONS,
    X_MEDIA_FIELDS,
    X_TWEET_FIELDS,
    X_USER_FIELDS,
)

logger = logging.getLogger(__name__)


class XFilteredStream(tweepy.StreamingClient):
    def __init__(
        self,
        bearer_token: str,
        on_event: Callable[[CanonicalEvent], None],
        *,
        mapper: XEventMapper | None = None,
    ):
        super().__init__(bearer_token, wait_on_rate_limit=False)
        self.event_callback = on_event
        self.mapper = mapper or XEventMapper()

    def on_response(self, response: Any) -> None:
        for event in self.mapper.map_response(response, mode="filtered_stream"):
            self.event_callback(event)

    def on_connection_error(self) -> None:
        logger.error(
            "X filtered stream connection failed",
            extra={"service": "x-stream", "platform": "x", "operation": "stream", "status": "FAIL"},
        )
        self.disconnect()

    def on_errors(self, errors: Any) -> None:
        logger.error(
            "X filtered stream returned errors",
            extra={
                "service": "x-stream",
                "platform": "x",
                "operation": "stream",
                "status": "FAIL",
                "error": str(errors),
            },
        )


class XStreamRunner:
    RULE_TAG_PREFIX = "social-sentinel:"

    def __init__(self, stream: XFilteredStream):
        self.stream = stream
        self.worker: Any | None = None

    def _managed_rule_ids(self) -> list[str]:
        existing = self.stream.get_rules()
        rules = getattr(existing, "data", None) or []
        return [
            rule.id
            for rule in rules
            if str(getattr(rule, "tag", "")).startswith(self.RULE_TAG_PREFIX)
        ]

    def replace_rules(self, queries: list[str]) -> None:
        cleaned = [query.strip() for query in queries if query.strip()]
        if not cleaned:
            raise ValueError("At least one non-empty X filtered-stream rule is required")
        self.clear_managed_rules()
        self.stream.add_rules(
            [
                tweepy.StreamRule(value=query, tag=f"{self.RULE_TAG_PREFIX}{index}")
                for index, query in enumerate(cleaned, start=1)
            ]
        )

    def clear_managed_rules(self) -> None:
        ids = self._managed_rule_ids()
        if ids:
            self.stream.delete_rules(ids)

    def run(self, *, threaded: bool = False) -> Any:
        self.worker = self.stream.filter(
            tweet_fields=X_TWEET_FIELDS,
            expansions=X_EXPANSIONS,
            user_fields=X_USER_FIELDS,
            media_fields=X_MEDIA_FIELDS,
            threaded=threaded,
        )
        return self.worker

    def stop(self) -> None:
        self.stream.disconnect()
        if (
            self.worker is not None
            and hasattr(self.worker, "join")
            and self.worker is not current_thread()
        ):
            self.worker.join(timeout=5)
