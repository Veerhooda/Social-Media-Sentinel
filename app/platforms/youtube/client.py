"""YouTube Data API v3 client boundary.

All google-api-python-client objects stay inside this module. Callers work
only with plain dictionaries shaped like the v3 responses, which keeps the
Google resource model from leaking downstream and makes tests deterministic
without network access.
"""
from __future__ import annotations

from typing import Any

from app.core.config import Settings, get_settings


class YouTubeAPIError(RuntimeError):
    """Transient or unexpected YouTube API failure (retryable candidates)."""


class YouTubeQuotaError(YouTubeAPIError):
    """Quota exhausted or access forbidden; do not hot-retry."""


class YouTubeNotConfiguredError(RuntimeError):
    """YOUTUBE_API_KEY is missing."""


class YouTubeCommentsDisabledError(RuntimeError):
    """The video has comments disabled; not a failure of the adapter."""


def _reason(error: Any) -> str:
    try:
        payload = error.resp  # type: ignore[union-attr]
        status = getattr(payload, "status", None)
        content = getattr(payload, "reason", "") or ""
        details = ""
        try:
            import json

            body = json.loads(error.content.decode("utf-8"))  # type: ignore[union-attr]
            items = body.get("error", {}).get("errors", [])
            details = ";".join(
                str(item.get("reason", "")) for item in items if isinstance(item, dict)
            )
        except Exception:  # noqa: BLE001 -- error introspection is best-effort
            details = ""
        return f"{status}:{content}:{details}"
    except Exception:  # noqa: BLE001 -- never fail while classifying a failure
        return str(error)


class YouTubeClient:
    def __init__(self, settings: Settings | None = None, *, service: Any | None = None):
        self.settings = settings or get_settings()
        self._service = service

    @property
    def configured(self) -> bool:
        return bool(self.settings.youtube_api_key)

    def _require_service(self) -> Any:
        if self._service is not None:
            return self._service
        api_key = self.settings.youtube_api_key
        if not api_key:
            raise YouTubeNotConfiguredError("YOUTUBE_API_KEY is not configured")
        from googleapiclient.discovery import build

        self._service = build("youtube", "v3", developerKey=api_key, cache_discovery=False)
        return self._service

    def comment_threads(
        self, video_id: str, *, page_token: str | None = None, max_results: int = 50
    ) -> dict[str, Any]:
        try:
            kwargs = {
                "part": "snippet,replies",
                "videoId": video_id,
                "maxResults": max(1, min(100, max_results)),
                "textFormat": "plainText",
            }
            if page_token:
                kwargs["pageToken"] = page_token
            request = self._require_service().commentThreads().list(**kwargs)
            return request.execute()
        except YouTubeNotConfiguredError:
            raise
        except Exception as exc:  # noqa: BLE001 -- mapped below by reason inspection
            raise self._classify(exc) from exc

    def comments_list(
        self, parent_id: str, *, page_token: str | None = None, max_results: int = 50
    ) -> dict[str, Any]:
        try:
            kwargs = {
                "part": "snippet",
                "parentId": parent_id,
                "maxResults": max(1, min(100, max_results)),
                "textFormat": "plainText",
            }
            if page_token:
                kwargs["pageToken"] = page_token
            request = self._require_service().comments().list(**kwargs)
            return request.execute()
        except YouTubeNotConfiguredError:
            raise
        except Exception as exc:  # noqa: BLE001 -- mapped below by reason inspection
            raise self._classify(exc) from exc

    @staticmethod
    def _classify(error: Exception) -> Exception:
        signature = _reason(error)
        lowered = signature.lower()
        if "commentsdisabled" in lowered or "videocommentsdisabled" in lowered:
            return YouTubeCommentsDisabledError(f"comments disabled: {signature}")
        if "quotaexceeded" in lowered or "dailylimitexceeded" in lowered:
            return YouTubeQuotaError(f"YouTube quota exhausted: {signature}")
        if "accessnotconfigured" in lowered or str(getattr(getattr(error, "resp", None), "status", "")) == "403":
            return YouTubeAPIError(f"YouTube access denied: {signature}")
        return YouTubeAPIError(f"youtube request failed: {signature}")
