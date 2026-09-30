"""Bounded YouTube comment retrieval with safe pagination.

Strategy: ``commentThreads.list`` for top-level comments (with whatever
inline replies the API returns), then ``comments.list`` only for threads
whose ``totalReplyCount`` exceeds the inline reply count. Page loops are
bounded by page count and total results, page tokens always advance, and
comments-disabled videos yield an honest empty result instead of an error.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from app.models.events import CanonicalEvent
from app.platforms.youtube.client import (
    YouTubeAPIError,
    YouTubeClient,
    YouTubeCommentsDisabledError,
)
from app.platforms.youtube.mapper import map_comment, thread_root_and_replies
from app.platforms.youtube.models import YouTubeCheckpoint, YouTubeCommentResult

logger = logging.getLogger(__name__)


class YouTubeComments:
    def __init__(self, client: YouTubeClient):
        self.client = client

    def fetch(
        self,
        video_id: str,
        *,
        max_results: int = 50,
        max_pages: int = 2,
        max_api_calls: int = 10,
        checkpoint: YouTubeCheckpoint | None = None,
    ) -> tuple[list[CanonicalEvent], YouTubeCommentResult]:
        if not video_id:
            raise ValueError("video_id is required")
        if not 1 <= max_results <= 500:
            raise ValueError("max_results must be between 1 and 500")
        if not 1 <= max_pages <= 20:
            raise ValueError("max_pages must be between 1 and 20")
        if not 1 <= max_api_calls <= 100:
            raise ValueError("max_api_calls must be between 1 and 100")
        if checkpoint and checkpoint.video_id != video_id:
            raise ValueError("checkpoint belongs to a different video")
        collected_at = datetime.now(UTC)
        events: list[CanonicalEvent] = []
        seen: set[str] = set()
        duplicates = 0
        rejected = 0
        replies_collected = 0
        incomplete_threads = 0
        pages = 0
        page_token = checkpoint.page_token if checkpoint else None
        thread_offset = checkpoint.thread_offset if checkpoint else 0
        comment_offset = checkpoint.comment_offset if checkpoint else 0
        reply_page_token = checkpoint.reply_page_token if checkpoint else None
        reply_offset = checkpoint.reply_offset if checkpoint else 0
        requested_tokens: set[str | None] = set()
        already = checkpoint.collected_count if checkpoint else 0
        remaining_calls = [max_api_calls]

        exhausted = False
        try:
            while pages < max_pages and len(events) < max_results:
                if not remaining_calls[0]:
                    return events, self._result(
                        video_id, events, replies_collected, duplicates, pages,
                        YouTubeCheckpoint(
                            video_id=video_id, page_token=page_token,
                            collected_count=already + len(events),
                        ), incomplete_threads, rejected, max_api_calls - remaining_calls[0],
                    )
                if page_token in requested_tokens:
                    raise YouTubeAPIError("YouTube repeated a page token; pagination stopped")
                requested_tokens.add(page_token)
                pages += 1
                remaining_calls[0] -= 1
                response = self.client.comment_threads(
                    video_id, page_token=page_token, max_results=50,
                )
                if not isinstance(response, dict) or not isinstance(response.get("items"), list):
                    raise YouTubeAPIError("YouTube returned a malformed comment thread page")
                page_items = response.get("items", []) or []
                for thread_index in range(thread_offset, len(page_items)):
                    thread = page_items[thread_index]
                    try:
                        top, inline, raw_replies, total = thread_root_and_replies(
                            thread, video_id=video_id, collected_at=collected_at,
                        )
                    except (AttributeError, TypeError, ValueError) as exc:
                        rejected += 1
                        logger.warning(
                            "Rejected malformed YouTube thread",
                            extra={"platform": "youtube", "operation": "normalize", "status": "FAIL", "error": str(exc)},
                        )
                        continue
                    thread_events = [top, *inline]
                    inline_ids = {item.get("id") for item in raw_replies if item.get("id")}
                    needs_more_replies = total > len(inline)
                    for event_index in range(comment_offset, len(thread_events)):
                        event = thread_events[event_index]
                        if len(events) >= max_results:
                            return events, self._result(
                                video_id, events, replies_collected, duplicates, pages,
                                YouTubeCheckpoint(
                                    video_id=video_id, page_token=page_token,
                                    thread_offset=thread_index, comment_offset=event_index,
                                    collected_count=already + len(events),
                                ), incomplete_threads, rejected, max_api_calls - remaining_calls[0],
                            )
                        if self._add(events, seen, event):
                            replies_collected += int(event.parent_platform_post_id is not None)
                        else:
                            duplicates += 1
                    if needs_more_replies:
                        if len(events) >= max_results or not remaining_calls[0]:
                            return events, self._result(
                                video_id, events, replies_collected, duplicates, pages,
                                YouTubeCheckpoint(
                                    video_id=video_id, page_token=page_token,
                                    thread_offset=thread_index,
                                    comment_offset=len(thread_events),
                                    reply_page_token=reply_page_token,
                                    reply_offset=reply_offset,
                                    collected_count=already + len(events),
                                ), incomplete_threads + 1, rejected,
                                max_api_calls - remaining_calls[0],
                            )
                        extra, next_reply_token, next_reply_offset, complete = self._complete_replies(
                            video_id, top.platform_post_id, inline_ids,
                            top.author.platform_user_id if top.source_metadata["author_id_source"] == "channel_id" else None,
                            collected_at, remaining_calls, max_results - len(events),
                            page_token=reply_page_token, item_offset=reply_offset,
                        )
                        for event in extra:
                            if self._add(events, seen, event):
                                replies_collected += 1
                            else:
                                duplicates += 1
                        if not complete:
                            return events, self._result(
                                video_id, events, replies_collected, duplicates, pages,
                                YouTubeCheckpoint(
                                    video_id=video_id, page_token=page_token,
                                    thread_offset=thread_index,
                                    comment_offset=len(thread_events),
                                    reply_page_token=next_reply_token,
                                    reply_offset=next_reply_offset,
                                    collected_count=already + len(events),
                                ), incomplete_threads + 1, rejected,
                                max_api_calls - remaining_calls[0],
                            )
                    comment_offset = 0
                    reply_page_token = None
                    reply_offset = 0
                thread_offset = 0
                next_page_token = response.get("nextPageToken")
                if next_page_token and next_page_token in requested_tokens:
                    raise YouTubeAPIError("YouTube repeated a page token; pagination stopped")
                page_token = next_page_token
                if not page_token:
                    exhausted = True
                    break
        except YouTubeCommentsDisabledError as exc:
            if events:
                raise YouTubeAPIError(
                    "YouTube disabled comments after partial retrieval; retry from the last checkpoint"
                ) from exc
            return [], YouTubeCommentResult(
                video_id=video_id,
                exhausted=True,
                api_calls=max_api_calls - remaining_calls[0],
                next_checkpoint=YouTubeCheckpoint(video_id=video_id, collected_count=already),
                detail=str(exc),
            )

        return events, self._result(
            video_id, events, replies_collected, duplicates, pages,
            YouTubeCheckpoint(
                video_id=video_id, page_token=page_token if not exhausted else None,
                collected_count=already + len(events),
            ), incomplete_threads, rejected, max_api_calls - remaining_calls[0],
            exhausted=exhausted,
        )

    @staticmethod
    def _result(
        video_id: str,
        events: list[CanonicalEvent],
        replies_collected: int,
        duplicates: int,
        pages: int,
        checkpoint: YouTubeCheckpoint,
        incomplete_threads: int,
        rejected: int,
        api_calls: int,
        *,
        exhausted: bool = False,
    ) -> YouTubeCommentResult:
        return YouTubeCommentResult(
            video_id=video_id,
            exhausted=exhausted,
            comments_collected=len(events) - replies_collected,
            replies_collected=replies_collected,
            duplicates_skipped=duplicates,
            pages_fetched=pages,
            api_calls=api_calls,
            next_checkpoint=checkpoint,
            incomplete_threads=incomplete_threads,
            rejected_count=rejected,
            detail=f"collected {len(events)} comments from {pages} pages",
        )

    def _complete_replies(
        self,
        video_id: str,
        top_id: str,
        known_ids: set[str],
        parent_author_id: str | None,
        collected_at: datetime,
        remaining_calls: list[int],
        max_events: int,
        *,
        page_token: str | None = None,
        item_offset: int = 0,
    ) -> tuple[list[CanonicalEvent], str | None, int, bool]:
        """Return a bounded reply segment and the position for safe resumption.

        A page interrupted by the event limit is fetched again on resume and
        ``item_offset`` skips only replies already returned. More than five
        reply pages in one pass are reported as incomplete.
        """
        events: list[CanonicalEvent] = []
        requested_tokens: set[str | None] = set()
        pages = 0
        while pages < 5:
            if not remaining_calls[0]:
                return events, page_token, item_offset, False
            if page_token in requested_tokens:
                raise YouTubeAPIError("YouTube repeated a reply page token")
            requested_tokens.add(page_token)
            pages += 1
            remaining_calls[0] -= 1
            response = self.client.comments_list(
                top_id, page_token=page_token, max_results=100,
            )
            if not isinstance(response, dict) or not isinstance(response.get("items"), list):
                raise YouTubeAPIError("YouTube returned a malformed reply page")
            for item_index in range(item_offset, len(response["items"])):
                item = response["items"][item_index]
                if not isinstance(item, dict):
                    logger.warning("Rejected malformed YouTube reply item")
                    continue
                reply_id = item.get("id") or ""
                if not reply_id or reply_id in known_ids:
                    continue
                if len(events) >= max_events:
                    return events, page_token, item_index, False
                snippet = item.get("snippet") or {}
                try:
                    events.append(
                        map_comment(
                            snippet, reply_id, video_id=video_id, thread_root_id=top_id,
                            parent_comment_id=snippet.get("parentId") or top_id,
                            parent_author_id=parent_author_id, collected_at=collected_at,
                        )
                    )
                except (AttributeError, TypeError, ValueError) as exc:
                    logger.warning("Rejected malformed YouTube reply", extra={"platform": "youtube", "operation": "normalize", "status": "FAIL", "error": str(exc)})
            next_page_token = response.get("nextPageToken")
            if next_page_token and next_page_token in requested_tokens:
                raise YouTubeAPIError("YouTube repeated a reply page token")
            page_token = next_page_token
            item_offset = 0
            if not page_token:
                # Some replies may be deleted or hidden even if the reported
                # total is larger; pagination exhaustion is the only evidence
                # that the API has no more pages to expose.
                return events, None, 0, True
        return events, page_token, 0, False

    @staticmethod
    def _add(events: list[CanonicalEvent], seen: set[str], event: CanonicalEvent) -> bool:
        if event.platform_post_id in seen:
            return False
        seen.add(event.platform_post_id)
        events.append(event)
        return True
