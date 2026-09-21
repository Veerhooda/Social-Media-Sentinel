from __future__ import annotations

import threading
import time

from app.scheduler.schemas import JobExecutionResult, JobRunStatus
from app.scheduler.service import SchedulerService


def test_scheduler_startup_executes_job_and_shutdown_is_clean() -> None:
    calls = []
    scheduler = SchedulerService(enabled=True, tick_seconds=0.01)
    scheduler.register(
        "job",
        60,
        lambda: calls.append("run") or JobExecutionResult(processed_count=2),
    )

    scheduler.start(run_immediately=True)
    assert scheduler.wait_for_idle(timeout=1)
    status = scheduler.get_job_status("job")
    scheduler.stop(timeout=1)

    assert calls == ["run"]
    assert status.status is JobRunStatus.PASS
    assert status.processed_count == 2
    assert status.total_processed_count == 2
    assert status.last_started_at is not None
    assert status.last_finished_at is not None
    assert status.next_run_at is not None
    assert status.duration_ms is not None
    assert scheduler.snapshot().running is False


def test_failed_job_is_observable_without_crashing_scheduler() -> None:
    scheduler = SchedulerService(enabled=True)

    def fail() -> JobExecutionResult:
        raise RuntimeError("controlled failure")

    scheduler.register("failing", 10, fail)
    scheduler.register("healthy", 10, lambda: JobExecutionResult(processed_count=1))
    status = scheduler.run_job_now("failing")
    healthy = scheduler.run_job_now("healthy")

    assert status.status is JobRunStatus.FAIL
    assert "controlled failure" in status.error
    assert status.run_count == 1
    assert healthy.status is JobRunStatus.PASS
    assert healthy.processed_count == 1


def test_overlapping_job_is_prevented() -> None:
    started = threading.Event()
    release = threading.Event()

    def blocking() -> JobExecutionResult:
        started.set()
        release.wait(1)
        return JobExecutionResult(processed_count=1)

    scheduler = SchedulerService(enabled=True, tick_seconds=0.01)
    scheduler.register("blocking", 60, blocking)
    scheduler.start(run_immediately=True)
    assert started.wait(1)

    scheduler.run_job_now("blocking")
    assert scheduler.get_job_status("blocking").overlap_skips == 1

    release.set()
    assert scheduler.wait_for_idle(timeout=1)
    scheduler.stop(timeout=1)
    assert scheduler.get_job_status("blocking").run_count == 1


def test_stop_waits_for_short_active_job() -> None:
    started = threading.Event()

    def short_job() -> JobExecutionResult:
        started.set()
        time.sleep(0.05)
        return JobExecutionResult(processed_count=1)

    scheduler = SchedulerService(enabled=True, tick_seconds=0.01)
    scheduler.register("short", 60, short_job)
    scheduler.start(run_immediately=True)
    assert started.wait(1)
    scheduler.stop(timeout=1)

    snapshot = scheduler.snapshot()
    assert snapshot.running is False
    assert snapshot.jobs[0].status is JobRunStatus.PASS
    assert snapshot.jobs[0].last_finished_at is not None
