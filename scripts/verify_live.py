"""Smoke-check a running API: every dashboard endpoint answers, data is stored and collection is fresh.

Usage: uv run python scripts/verify_live.py [base_url]   (default http://127.0.0.1:8000/api)
Exit code 1 if any endpoint fails. Never prints secrets.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000/api").rstrip("/")
ENDPOINTS = [
    "/health", "/system/jobs", "/sources", "/events?limit=1", "/events/enriched?limit=1",
    "/analytics/sentiment", "/analytics/emotions", "/analytics/topics", "/analytics/trends",
    "/analytics/demographics", "/network/graph", "/network/summary", "/audience-lab/status",
]


def get(path: str) -> tuple[int, object, float]:
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(BASE + path, timeout=30) as response:
            return response.status, json.loads(response.read() or b"null"), time.perf_counter() - started
    except urllib.error.HTTPError as error:
        return error.code, None, time.perf_counter() - started
    except (urllib.error.URLError, TimeoutError) as error:
        return 0, str(error), time.perf_counter() - started


def main() -> int:
    failures = 0
    bodies: dict[str, object] = {}
    for path in ENDPOINTS:
        status, body, took = get(path)
        ok = status == 200
        failures += not ok
        bodies[path] = body
        print(f"{'PASS' if ok else 'FAIL'} {status:>3} {took * 1000:>6.0f} ms  {path}")
    health = bodies.get("/health") if isinstance(bodies.get("/health"), dict) else {}
    if health:
        print(f"\nstored events: {health.get('event_count')} (real {health.get('real_event_count')})")
        now = datetime.now(UTC)
        for platform in health.get("platforms", []):
            latest = platform.get("latest_collected_at")
            age = (now - datetime.fromisoformat(latest.replace("Z", "+00:00"))).total_seconds() / 60 if latest else None
            age_text = f"{age:.0f} min ago" if age is not None else "never"
            print(f"  {platform['platform']:<9} {platform['real_event_count']:>6} events, last collected {age_text}")
    jobs = bodies.get("/system/jobs") if isinstance(bodies.get("/system/jobs"), dict) else {}
    if jobs:
        print(f"\nscheduler running: {jobs.get('running')}")
        for job in jobs.get("jobs", []):
            print(f"  {job['status']:<8} {job['name']:<24} runs={job['run_count']:<4} {job.get('detail') or job.get('error') or ''}"[:140])
    print("\nRESULT:", "PASS" if failures == 0 else f"FAIL ({failures} endpoints)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
