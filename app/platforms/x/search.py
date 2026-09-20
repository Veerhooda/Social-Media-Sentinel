from __future__ import annotations

from datetime import datetime
from typing import Any

from app.platforms.x.client import XClient
from app.platforms.x.mapper import XEventMapper
from app.platforms.x.models import (
    X_EXPANSIONS,
    X_MEDIA_FIELDS,
    X_TWEET_FIELDS,
    X_USER_FIELDS,
    XSearchResult,
)


class XRecentSearch:
    def __init__(self, x_client: XClient, mapper: XEventMapper | None = None):
        self.x_client = x_client
        self.mapper = mapper or XEventMapper()

    def search(
        self,
        query: str,
        *,
        max_results: int = 100,
        max_pages: int | None = 1,
        since_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> XSearchResult:
        if not query.strip():
            raise ValueError("X recent-search query must not be empty")
        if not 10 <= max_results <= 100:
            raise ValueError("X recent-search max_results must be between 10 and 100")

        client = self.x_client.require_client()
        events = []
        next_token: str | None = None
        pages_fetched = 0
        newest_id: str | None = None
        oldest_id: str | None = None

        while max_pages is None or pages_fetched < max_pages:
            kwargs: dict[str, Any] = {
                "query": query,
                "max_results": max_results,
                "tweet_fields": X_TWEET_FIELDS,
                "expansions": X_EXPANSIONS,
                "user_fields": X_USER_FIELDS,
                "media_fields": X_MEDIA_FIELDS,
            }
            if next_token:
                kwargs["next_token"] = next_token
            if since_id:
                kwargs["since_id"] = since_id
            if start_time:
                kwargs["start_time"] = start_time
            if end_time:
                kwargs["end_time"] = end_time

            response = self.x_client.execute(
                "recent_search", lambda kwargs=kwargs: client.search_recent_tweets(**kwargs)
            )
            pages_fetched += 1
            events.extend(self.mapper.map_response(response, mode="recent_search", query=query))
            meta = getattr(response, "meta", None) or {}
            newest_id = newest_id or meta.get("newest_id")
            oldest_id = meta.get("oldest_id") or oldest_id
            next_token = meta.get("next_token")
            if not next_token:
                break

        return XSearchResult(
            events=events,
            pages_fetched=pages_fetched,
            newest_id=newest_id,
            oldest_id=oldest_id,
        )

