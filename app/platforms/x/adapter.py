from __future__ import annotations

from collections.abc import Callable
from threading import Event

from app.core.config import Settings, get_settings
from app.models.events import CanonicalEvent
from app.platforms.x.client import XAPIError, XAuthenticationError, XClient
from app.platforms.x.mapper import XEventMapper
from app.platforms.x.models import XHealth, XSearchResult
from app.platforms.x.search import XRecentSearch
from app.platforms.x.stream import XFilteredStream, XStreamRunner


class XAdapter:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        x_client: XClient | None = None,
        mapper: XEventMapper | None = None,
    ):
        self.settings = settings or get_settings()
        self.mapper = mapper or XEventMapper()
        self.x_client = x_client or XClient(self.settings)
        self.search_service = XRecentSearch(self.x_client, self.mapper)

    def search_recent(
        self,
        query: str | None = None,
        *,
        max_results: int | None = None,
        max_pages: int | None = 1,
        since_id: str | None = None,
    ) -> XSearchResult:
        return self.search_service.search(
            query if query is not None else self.settings.x_query,
            max_results=max_results or self.settings.x_max_results,
            max_pages=max_pages,
            since_id=since_id,
        )

    def poll_recent(
        self,
        on_event: Callable[[CanonicalEvent], None],
        *,
        query: str | None = None,
        stop_event: Event | None = None,
        max_pages: int | None = 1,
    ) -> None:
        stop = stop_event or Event()
        since_id: str | None = None
        while not stop.is_set():
            result = self.search_recent(query, max_pages=max_pages, since_id=since_id)
            for event in sorted(result.events, key=lambda item: item.created_at):
                on_event(event)
            since_id = result.newest_id or since_id
            if stop.wait(self.settings.x_search_interval_seconds):
                break

    def stream(
        self,
        on_event: Callable[[CanonicalEvent], None],
        *,
        queries: list[str] | None = None,
        threaded: bool = False,
    ) -> XStreamRunner:
        if not self.settings.x_bearer_token:
            raise RuntimeError("X_BEARER_TOKEN is required for filtered stream")
        stream = XFilteredStream(self.settings.x_bearer_token, on_event, mapper=self.mapper)
        runner = XStreamRunner(stream)
        self.x_client.execute(
            "filtered_stream_rules",
            lambda: runner.replace_rules(queries or [self.settings.x_query]),
        )
        self.x_client.execute(
            "filtered_stream_connect",
            lambda: runner.run(threaded=threaded),
        )
        return runner

    def health_check(self, *, live: bool = False) -> XHealth:
        if not self.x_client.configured:
            return XHealth(
                status="SKIPPED",
                configured=False,
                live_checked=False,
                detail="X_BEARER_TOKEN is not configured",
            )
        if not live:
            return XHealth(
                status="PASS",
                configured=True,
                live_checked=False,
                detail="X client configured; live request not requested",
            )
        client = self.x_client.require_client()
        try:
            self.x_client.execute(
                "health_check",
                lambda: client.get_user(username="XDevelopers"),
            )
        except (XAPIError, XAuthenticationError) as exc:
            return XHealth(
                status="UNAVAILABLE", configured=True, live_checked=True, detail=str(exc)
            )
        return XHealth(
            status="PASS", configured=True, live_checked=True, detail="X API request succeeded"
        )
