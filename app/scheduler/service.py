from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from app.scheduler.schemas import (
    JobExecutionResult,
    JobRunStatus,
    JobStatus,
    SchedulerStatus,
)

logger = logging.getLogger(__name__)
JobCallable = Callable[[], JobExecutionResult]


@dataclass
class _ScheduledJob:
    name: str
    interval_seconds: float
    operation: JobCallable
    status: JobStatus
    lock: threading.Lock = field(default_factory=threading.Lock)


class SchedulerService:
    def __init__(
        self,
        *,
        enabled: bool = True,
        tick_seconds: float = 1.0,
        clock: Callable[[], datetime] | None = None,
    ):
        self.enabled = enabled
        self.tick_seconds = tick_seconds
        self.clock = clock or (lambda: datetime.now(UTC))
        self._jobs: dict[str, _ScheduledJob] = {}
        self._state_lock = threading.RLock()
        self._stop_event = threading.Event()
        self._loop_thread: threading.Thread | None = None
        self._active_threads: set[threading.Thread] = set()
        self._running = False
        self._started_at: datetime | None = None
        self._stopped_at: datetime | None = None

    def register(self, name: str, interval_seconds: float, operation: JobCallable) -> None:
        if interval_seconds <= 0:
            raise ValueError("job interval must be positive")
        with self._state_lock:
            if self._running:
                raise RuntimeError("cannot register jobs after scheduler startup")
            if name in self._jobs:
                raise ValueError(f"job already registered: {name}")
            self._jobs[name] = _ScheduledJob(
                name=name,
                interval_seconds=interval_seconds,
                operation=operation,
                status=JobStatus(name=name, interval_seconds=interval_seconds),
            )

    def start(self, *, run_immediately: bool = True) -> None:
        with self._state_lock:
            if self._running or not self.enabled:
                return
            now = self.clock()
            self._running = True
            self._started_at = now
            self._stopped_at = None
            self._stop_event.clear()
            for job in self._jobs.values():
                job.status.next_run_at = (
                    now if run_immediately else now + timedelta(seconds=job.interval_seconds)
                )
            self._loop_thread = threading.Thread(
                target=self._loop,
                name="social-sentinel-scheduler",
                daemon=True,
            )
            self._loop_thread.start()

    def stop(self, *, timeout: float = 30.0) -> None:
        self._stop_event.set()
        loop_thread = self._loop_thread
        if loop_thread is not None and loop_thread is not threading.current_thread():
            loop_thread.join(timeout=timeout)

        deadline = time.monotonic() + timeout
        while True:
            with self._state_lock:
                active = [thread for thread in self._active_threads if thread.is_alive()]
            if not active or time.monotonic() >= deadline:
                break
            active[0].join(timeout=max(0.0, deadline - time.monotonic()))

        with self._state_lock:
            self._running = False
            self._stopped_at = self.clock()

    def run_job_now(self, name: str) -> JobStatus:
        job = self._jobs[name]
        self._execute_job(job)
        return self.get_job_status(name)

    def dispatch_due_jobs(self) -> None:
        now = self.clock()
        with self._state_lock:
            jobs = list(self._jobs.values())
        for job in jobs:
            if job.status.next_run_at is None or job.status.next_run_at > now:
                continue
            if job.lock.locked():
                with self._state_lock:
                    job.status.overlap_skips += 1
                    job.status.next_run_at = now + timedelta(seconds=job.interval_seconds)
                continue
            with self._state_lock:
                job.status.next_run_at = now + timedelta(seconds=job.interval_seconds)
            thread = threading.Thread(
                target=self._execute_job,
                args=(job,),
                name=f"job-{job.name}",
                daemon=True,
            )
            with self._state_lock:
                self._active_threads.add(thread)
            thread.start()

    def wait_for_idle(self, *, timeout: float = 30.0) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self._state_lock:
                active = bool(self._active_threads)
                now = self.clock()
                due = any(
                    job.status.run_count == 0
                    and job.status.next_run_at is not None
                    and job.status.next_run_at <= now
                    for job in self._jobs.values()
                )
            if not active and not due:
                return True
            time.sleep(0.01)
        return False

    def get_job_status(self, name: str) -> JobStatus:
        with self._state_lock:
            return self._jobs[name].status.model_copy(deep=True)

    def snapshot(self) -> SchedulerStatus:
        with self._state_lock:
            return SchedulerStatus(
                enabled=self.enabled,
                running=self._running,
                started_at=self._started_at,
                stopped_at=self._stopped_at,
                jobs=[
                    self._jobs[name].status.model_copy(deep=True)
                    for name in sorted(self._jobs)
                ],
            )

    def _loop(self) -> None:
        self.dispatch_due_jobs()
        while not self._stop_event.wait(self.tick_seconds):
            self.dispatch_due_jobs()

    def _execute_job(self, job: _ScheduledJob) -> None:
        if not job.lock.acquire(blocking=False):
            with self._state_lock:
                job.status.overlap_skips += 1
            return
        started = self.clock()
        monotonic_started = time.monotonic()
        with self._state_lock:
            job.status.status = JobRunStatus.RUNNING
            job.status.last_started_at = started
            job.status.error = None
            job.status.detail = None
        try:
            result = job.operation()
            with self._state_lock:
                job.status.status = result.status
                job.status.processed_count = result.processed_count
                job.status.total_processed_count += result.processed_count
                job.status.detail = result.detail
        except Exception as exc:
            with self._state_lock:
                job.status.status = JobRunStatus.FAIL
                job.status.processed_count = int(getattr(exc, "processed_count", 0))
                job.status.total_processed_count += job.status.processed_count
                job.status.error = f"{type(exc).__name__}: {exc}"
            logger.exception(
                "Scheduled job failed",
                extra={
                    "service": "scheduler",
                    "operation": job.name,
                    "status": "FAIL",
                    "error": str(exc),
                },
            )
        finally:
            finished = self.clock()
            duration_ms = (time.monotonic() - monotonic_started) * 1000
            with self._state_lock:
                job.status.last_finished_at = finished
                job.status.duration_ms = duration_ms
                job.status.run_count += 1
                job.status.next_run_at = finished + timedelta(seconds=job.interval_seconds)
            logger.info(
                "Scheduled job completed",
                extra={
                    "service": "scheduler",
                    "operation": job.name,
                    "duration_ms": round(duration_ms, 2),
                    "processed_count": job.status.processed_count,
                    "started_at": started.isoformat(),
                    "finished_at": finished.isoformat(),
                    "status": job.status.status.value,
                    "error": job.status.error,
                },
            )
            job.lock.release()
            with self._state_lock:
                self._active_threads.discard(threading.current_thread())
