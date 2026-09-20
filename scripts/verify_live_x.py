from __future__ import annotations

import argparse
import json
from datetime import datetime

from fastapi.testclient import TestClient

from app.db.repositories.social import SocialRepository
from app.db.session import SessionLocal
from app.main import app
from app.nlp.service import NLPService
from app.pipeline.service import EventPipeline
from app.platforms.x.adapter import XAdapter
from app.platforms.x.client import XAPIError, XAuthenticationError


def main() -> int:
    parser = argparse.ArgumentParser(description="Bounded, privacy-conscious live X verification")
    parser.add_argument("--query", default=None)
    parser.add_argument("--max-results", type=int, default=10)
    parser.add_argument("--start-time", type=datetime.fromisoformat, default=None)
    parser.add_argument("--end-time", type=datetime.fromisoformat, default=None)
    args = parser.parse_args()

    try:
        search = XAdapter().search_recent(
            args.query,
            max_results=args.max_results,
            max_pages=1,
            start_time=args.start_time,
            end_time=args.end_time,
        )
    except (XAPIError, XAuthenticationError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc).replace("\n", " | ")}))
        return 2

    events = search.events
    if not events:
        print(json.dumps({"status": "FAIL", "error": "Recent Search returned zero posts"}))
        return 3

    event_ids = {event.platform_post_id for event in events}
    referenced = [event for event in events if event.source_metadata.get("referenced_posts")]
    referenced_mapped = [
        event
        for event in referenced
        if event.parent_platform_post_id
        or event.relationships.parent_author_id
        or event.relationships.repost_of_author_id
        or event.relationships.quote_of_event_id
    ]

    with SessionLocal() as session:
        repository = SocialRepository(session)
        pipeline = EventPipeline(repository, NLPService())
        first_results = [pipeline.process(event) for event in events]
        duplicate_results = [pipeline.process(event) for event in events]
        stored_events = [
            event
            for event in repository.list_events(limit=1000, platform="x")
            if event.platform_post_id in event_ids
        ]
        analyzed = [
            (event, result)
            for event, result in repository.list_nlp_results()
            if event.platform_post_id in event_ids
        ]
        live_edges = [
            edge for edge in repository.list_graph_edges() if edge.event_id in {e.event_id for e in events}
        ]

    with TestClient(app) as client:
        api_events_response = client.get("/api/events", params={"limit": 1000, "platform": "x"})
        sentiment_response = client.get("/api/analytics/sentiment")
        emotions_response = client.get("/api/analytics/emotions")
        network_response = client.get("/api/network/summary")
    api_events = api_events_response.json().get("items", [])
    api_ids = {item["platform_post_id"] for item in api_events}

    summary = {
        "status": "PASS",
        "pages_fetched": search.pages_fetched,
        "real_events_returned": len(events),
        "stored_first_pass": sum(result.stored for result in first_results),
        "duplicates_second_pass": sum(result.duplicate for result in duplicate_results),
        "post_ids_preserved": len({event.platform_post_id for event in stored_events} & event_ids),
        "source_timestamps_preserved": sum(event.created_at is not None for event in stored_events),
        "collection_timestamps_separate": sum(
            event.collected_at != event.created_at for event in stored_events
        ),
        "authors_mapped": sum(bool(event.author.platform_user_id) for event in stored_events),
        "hashtags_mapped": sum(len(event.content.hashtags) for event in stored_events),
        "mentions_mapped": sum(len(event.content.mentions) for event in stored_events),
        "public_metrics_records": sum(bool(event.metrics.model_dump()) for event in stored_events),
        "referenced_events_returned": len(referenced),
        "referenced_events_mapped": len(referenced_mapped),
        "nlp_results": len(analyzed),
        "real_sentiment_results": sum(bool(result.sentiment.label) for _, result in analyzed),
        "real_emotion_results": sum(bool(result.emotions.scores) for _, result in analyzed),
        "real_irony_results": sum(result.irony.confidence is not None for _, result in analyzed),
        "graph_edges_from_batch": len(live_edges),
        "api_events_status": api_events_response.status_code,
        "api_batch_events_visible": len(api_ids & event_ids),
        "api_sentiment_status": sentiment_response.status_code,
        "api_emotions_status": emotions_response.status_code,
        "api_network_status": network_response.status_code,
    }
    print(json.dumps(summary, sort_keys=True))
    required_counts = [
        summary["post_ids_preserved"],
        summary["source_timestamps_preserved"],
        summary["collection_timestamps_separate"],
        summary["authors_mapped"],
        summary["nlp_results"],
        summary["api_batch_events_visible"],
    ]
    return 0 if all(value == len(events) for value in required_counts) else 4


if __name__ == "__main__":
    raise SystemExit(main())
