"""YouTube adapter: polling-based comment ingestion behind a clean interface.

Exposes ``collect`` (bounded retrieval for backfill/verification),
``poll_once`` (single scheduler-friendly pass, disabled by default), and
``health_check``. No long-lived streaming exists because the YouTube Data
API is polling-based; the adapter never claims otherwise.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from app.core.config import Settings, get_settings
from app.models.events import CanonicalEvent
from app.platforms.youtube.client import (
    YouTubeAPIError,
    YouTubeClient,
    YouTubeCommentsDisabledError,
    YouTubeNotConfiguredError,
    YouTubeQuotaError,
)
from app.platforms.youtube.comments import YouTubeComments
from app.platforms.youtube.models import (
    YouTubeCheckpoint,
    YouTubeCommentResult,
    YouTubeHealth,
    YouTubePollStats,
)


class YouTubeAdapter:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        youtube_client: YouTubeClient | None = None,
    ):
        self.settings = settings or get_settings()
        self.youtube_client = youtube_client or YouTubeClient(self.settings)
        self.comments_service = YouTubeComments(self.youtube_client)

    def collect(
        self,
        video_id: str,
        *,
        max_results: int | None = None,
        max_pages: int | None = None,
        max_api_calls: int | None = None,
        checkpoint: YouTubeCheckpoint | None = None,
    ) -> tuple[list[CanonicalEvent], YouTubeCommentResult]:
        return self.comments_service.fetch(
            video_id,
            max_results=self.settings.youtube_max_results if max_results is None else max_results,
            max_pages=self.settings.youtube_max_pages if max_pages is None else max_pages,
            max_api_calls=self.settings.youtube_max_api_calls if max_api_calls is None else max_api_calls,
            checkpoint=checkpoint,
        )

    def poll_once(
        self,
        on_event: Callable[[CanonicalEvent], None],
        *,
        video_id: str | None = None,
    ) -> YouTubePollStats:
        """Fetch one bounded batch and dispatch canonical events to the caller.

        The caller owns persistence and analytics. No polling job is registered
        with the scheduler; this method is invoked only explicitly.
        """
        target = video_id or self.settings.youtube_video_id
        started = datetime.now(UTC)
        if not target:
            return YouTubePollStats(
                video_id="", started_at=started, finished_at=datetime.now(UTC),
                detail="SKIPPED: YOUTUBE_VIDEO_ID is not configured",
            )
        try:
            events, result = self.collect(target)
        except YouTubeNotConfiguredError as exc:
            return YouTubePollStats(
                video_id=target, started_at=started, finished_at=datetime.now(UTC),
                detail=f"SKIPPED: {exc}",
            )
        except (YouTubeQuotaError, YouTubeAPIError):
            raise
        for event in events:
            on_event(event)
        return YouTubePollStats(
            video_id=target, comments_collected=len(events),
            started_at=started, finished_at=datetime.now(UTC),
            detail=f"{result.detail}; dispatched to caller",
        )

    def configuration_health(self) -> YouTubeHealth:
        if not self.youtube_client.configured:
            return YouTubeHealth(
                status="SKIPPED", configured=False, live_checked=False,
                detail="YOUTUBE_API_KEY is not configured",
            )
        return YouTubeHealth(
            status="PASS", configured=True, live_checked=False,
            detail="YouTube client configured; live request not requested",
        )

    def health_check(self, *, live: bool = False) -> YouTubeHealth:
        configured = self.configuration_health()
        if not live or not configured.configured:
            return configured
        video_id = self.settings.youtube_video_id
        if not video_id:
            return YouTubeHealth(
                status="SKIPPED", configured=True, live_checked=False,
                detail="YOUTUBE_VIDEO_ID is not configured; live check not requested",
            )
        try:
            self.youtube_client.comment_threads(video_id, max_results=1)
        except YouTubeCommentsDisabledError:
            return YouTubeHealth(
                status="PASS", configured=True, live_checked=True,
                detail="YouTube API reachable; comments are disabled for this video",
            )
        except (YouTubeQuotaError, YouTubeAPIError) as exc:
            return YouTubeHealth(
                status="UNAVAILABLE", configured=True, live_checked=True, detail=str(exc),
            )
        return YouTubeHealth(
            status="PASS", configured=True, live_checked=True,
            detail="YouTube API request succeeded",
        )
