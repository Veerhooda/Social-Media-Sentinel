from __future__ import annotations

import argparse
import json
import time

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.logging import configure_logging
from app.main import create_app
from app.scheduler.jobs import build_scheduler
from app.scheduler.schemas import JobRunStatus


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a bounded local analytics scheduler")
    parser.add_argument("--duration-seconds", type=int, default=20)
    parser.add_argument("--x-interval", type=int, default=60)
    parser.add_argument("--x-max-results", type=int, default=10)
    parser.add_argument("--nlp-interval", type=int, default=2)
    parser.add_argument("--trend-interval", type=int, default=8)
    parser.add_argument("--graph-interval", type=int, default=2)
    args = parser.parse_args()
    if not 5 <= args.duration_seconds <= 120:
        parser.error("--duration-seconds must be between 5 and 120")

    configure_logging()
    settings = Settings(
        scheduler_enabled=True,
        x_search_interval_seconds=args.x_interval,
        x_max_results=args.x_max_results,
        x_max_pages_per_run=1,
        nlp_processing_interval_seconds=args.nlp_interval,
        trend_interval_seconds=args.trend_interval,
        graph_interval_seconds=args.graph_interval,
    )
    scheduler = build_scheduler(settings)
    app = create_app(scheduler=scheduler, settings=settings)
    with TestClient(app) as client:
        time.sleep(args.duration_seconds)
        running_jobs = client.get("/api/system/jobs").json()
        running_health = client.get("/api/health").json()

    snapshot = scheduler.snapshot()
    inspection_app = create_app(settings=Settings(scheduler_enabled=False))
    with TestClient(inspection_app) as client:
        final_api = {
            "events": client.get("/api/events", params={"limit": 1000}).status_code,
            "sentiment": client.get("/api/analytics/sentiment").status_code,
            "trends": client.get("/api/analytics/trends").status_code,
            "network": client.get("/api/network/summary").status_code,
        }
    print(
        json.dumps(
            {
            "running_jobs": running_jobs,
            "running_health": running_health,
            "stopped_scheduler": snapshot.model_dump(mode="json"),
            "final_api": final_api,
            },
            sort_keys=True,
        )
    )
    failed = [job.name for job in snapshot.jobs if job.status is JobRunStatus.FAIL]
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
