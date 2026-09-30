"""One bounded YouTube video comment pass through the existing event pipeline.

Requires explicit credentials and video ID. The command has no scheduler or
loop; each invocation fetches at most the configured page and event limits.
"""
from __future__ import annotations

import argparse
import json

from app.core.config import get_settings
from app.db.repositories.social import SocialRepository
from app.db.session import SessionLocal
from app.nlp.service import NLPService
from app.pipeline.service import EventPipeline
from app.platforms.youtube.adapter import YouTubeAdapter
from app.platforms.youtube.client import YouTubeAPIError, YouTubeQuotaError


def main() -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Bounded YouTube video comment ingestion")
    parser.add_argument("--video-id", default=settings.youtube_video_id)
    parser.add_argument("--max-results", type=int, default=settings.youtube_max_results)
    parser.add_argument("--max-pages", type=int, default=settings.youtube_max_pages)
    parser.add_argument("--max-api-calls", type=int, default=settings.youtube_max_api_calls)
    args = parser.parse_args()

    adapter = YouTubeAdapter(settings)
    if not adapter.youtube_client.configured or not args.video_id:
        print(json.dumps({"status": "SKIPPED", "detail": "YOUTUBE_API_KEY and video ID are required"}))
        return 0

    try:
        events, retrieval = adapter.collect(
            args.video_id, max_results=args.max_results, max_pages=args.max_pages,
            max_api_calls=args.max_api_calls,
        )
    except (ValueError, YouTubeAPIError, YouTubeQuotaError) as exc:
        print(json.dumps({"status": "FAIL", "detail": str(exc)}))
        return 2

    stored = duplicates = edges = 0
    with SessionLocal() as session:
        pipeline = EventPipeline(SocialRepository(session), NLPService(settings))
        for event in events:
            result = pipeline.process(event)
            stored += int(result.stored)
            duplicates += int(result.duplicate)
            edges += result.graph_edges_created
    print(json.dumps({
        "status": "PASS",
        "fetched": len(events),
        "replies": retrieval.replies_collected,
        "stored": stored,
        "duplicates": duplicates,
        "graph_edges": edges,
        "rejected": retrieval.rejected_count,
        "incomplete_threads": retrieval.incomplete_threads,
        "pages": retrieval.pages_fetched,
        "api_calls": retrieval.api_calls,
        "exhausted": retrieval.exhausted,
        "next_checkpoint": retrieval.next_checkpoint.model_dump(mode="json"),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
