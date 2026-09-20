from __future__ import annotations

import argparse
import json
import sys
from threading import Event

from app.core.logging import configure_logging
from app.db.repositories.social import SocialRepository
from app.db.session import SessionLocal
from app.nlp.service import NLPService
from app.pipeline.service import EventPipeline
from app.platforms.x.adapter import XAdapter
from app.platforms.x.client import XAPIError, XAuthenticationError


def main() -> int:
    configure_logging()
    parser = argparse.ArgumentParser(description="Run the X filtered stream analytics path")
    parser.add_argument("--query", action="append", dest="queries")
    parser.add_argument("--stance-target", default=None)
    parser.add_argument("--duration-seconds", type=int, default=30)
    parser.add_argument("--max-events", type=int, default=3)
    args = parser.parse_args()
    if not 5 <= args.duration_seconds <= 120:
        parser.error("--duration-seconds must be between 5 and 120")
    if not 1 <= args.max_events <= 20:
        parser.error("--max-events must be between 1 and 20")

    nlp_service = NLPService()
    finished = Event()
    counters = {"received": 0, "stored": 0, "duplicates": 0, "edges": 0}

    def process_event(event) -> None:
        if finished.is_set():
            return
        with SessionLocal() as session:
            result = EventPipeline(SocialRepository(session), nlp_service).process(
                event, stance_target=args.stance_target
            )
        counters["received"] += 1
        counters["stored"] += int(result.stored)
        counters["duplicates"] += int(result.duplicate)
        counters["edges"] += result.graph_edges_created
        if counters["received"] >= args.max_events:
            finished.set()

    adapter = XAdapter()
    runner = None
    cleanup_status = "NOT_REQUIRED"
    try:
        runner = adapter.stream(process_event, queries=args.queries, threaded=True)
        finished.wait(args.duration_seconds)
    except (XAPIError, XAuthenticationError) as exc:
        print(f"LIVE X STREAM: FAIL - {str(exc).replace(chr(10), ' | ')}", file=sys.stderr)
        return 2
    finally:
        if runner is not None:
            runner.stop()
            try:
                adapter.x_client.execute("filtered_stream_cleanup", runner.clear_managed_rules)
                cleanup_status = "PASS"
            except (XAPIError, XAuthenticationError) as exc:
                cleanup_status = f"FAIL: {str(exc).replace(chr(10), ' | ')}"

    status = "PASS" if counters["received"] else "FAIL"
    print(
        json.dumps(
            {
                "status": status,
                "duration_seconds": args.duration_seconds,
                "max_events": args.max_events,
                **counters,
                "rule_cleanup": cleanup_status,
            },
            sort_keys=True,
        )
    )
    return 0 if counters["received"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
