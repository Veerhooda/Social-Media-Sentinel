from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.api.dependencies import get_repository
from app.core.config import Settings
from app.main import create_app
from app.scheduler.jobs import GRAPH_JOB, NLP_JOB, TREND_JOB, X_COLLECTION_JOB
from app.scheduler.schemas import JobExecutionResult
from app.scheduler.service import SchedulerService


def test_health_and_jobs_api_expose_running_scheduler(repository) -> None:
    scheduler = SchedulerService(enabled=True, tick_seconds=0.01)
    for name in [X_COLLECTION_JOB, NLP_JOB, TREND_JOB, GRAPH_JOB]:
        scheduler.register(
            name,
            60,
            lambda: JobExecutionResult(processed_count=1, detail="controlled test run"),
        )
    app = create_app(
        scheduler=scheduler,
        settings=Settings(scheduler_enabled=True),
    )
    app.dependency_overrides[get_repository] = lambda: repository

    with TestClient(app) as client:
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            if all(job.run_count >= 1 for job in scheduler.snapshot().jobs):
                break
            time.sleep(0.01)
        jobs = client.get("/api/system/jobs")
        health = client.get("/api/health")

        assert jobs.status_code == 200
        assert jobs.json()["running"] is True
        assert len(jobs.json()["jobs"]) == 4
        assert all(item["run_count"] == 1 for item in jobs.json()["jobs"])
        assert all(item["total_processed_count"] == 1 for item in jobs.json()["jobs"])
        assert health.status_code == 200
        assert health.json()["database"]["status"] == "PASS"
        assert health.json()["event_count"] == health.json()["real_event_count"] + health.json()["replay_event_count"]
        assert health.json()["scheduler"]["status"] == "PASS"
        assert health.json()["analytics"]["status"] == "PASS"
        assert health.json()["x_api"]["status"] == "PASS"

    assert scheduler.snapshot().running is False
