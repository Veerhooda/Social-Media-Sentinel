"""Live progress, activity log and cancellation for Audience Lab background jobs.

Model calls run in worker threads; they only touch the in-memory tracker
(guarded by a lock). The job's own thread periodically writes the tracker
snapshot to the job row so the UI can show what is happening right now.
"""
from __future__ import annotations

import logging
import threading
import time
from collections import deque
from collections.abc import Callable, Iterable, Iterator
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import UTC, datetime
from typing import Any, TypeVar
from uuid import UUID

from app.audience_lab.llm import LLMError

log = logging.getLogger("app.audience_lab")
T = TypeVar("T")
R = TypeVar("R")
_CANCEL: dict[UUID, threading.Event] = {}
TICK_SECONDS = 2.0


class JobCancelled(LLMError):
    pass


def register(job_id: UUID) -> None:
    """Mark a job as owned by this process (called when it is queued)."""
    _CANCEL.setdefault(job_id, threading.Event())


def release(job_id: UUID) -> None:
    _CANCEL.pop(job_id, None)


def is_live(job_id: UUID) -> bool:
    return job_id in _CANCEL


def request_cancel(job_id: UUID) -> bool:
    flag = _CANCEL.get(job_id)
    if flag is None:
        return False
    flag.set()
    return True


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class JobTracker:
    def __init__(self, job_id: UUID, kind: str, flush: Callable[[dict[str, Any]], None] | None = None):
        self.job_id = job_id
        self.kind = kind
        self._flush = flush
        self._lock = threading.Lock()
        self._cancel = _CANCEL.setdefault(job_id, threading.Event())
        self._last_flush = 0.0
        self._t0 = time.monotonic()
        self.state: dict[str, Any] = {
            "stage": "starting", "step": None, "steps": None, "done": 0, "total": 0,
            "started_at": _now(), "stage_started_at": _now(), "last_activity_at": _now(),
            "calls": {"in_flight": 0, "finished": 0, "failed": 0, "retries": 0},
            "tokens": {"prompt": 0, "completion": 0, "reasoning": 0},
            "events": [],
        }
        self._events: deque[dict[str, Any]] = deque(maxlen=40)

    # -- state changes (any thread) -------------------------------------
    def _touch(self) -> None:
        self.state["last_activity_at"] = _now()

    def event(self, message: str, level: str = "info") -> None:
        with self._lock:
            self._events.append({"at": _now(), "level": level, "message": message})
            self._touch()
        log.log(logging.WARNING if level == "warn" else logging.INFO, "[%s %s] %s", self.kind, str(self.job_id)[:8], message)

    def stage(self, stage: str, total: int = 0, *, step: int | None = None, steps: int | None = None, message: str | None = None) -> None:
        with self._lock:
            self.state.update(stage=stage, total=total, done=0, stage_started_at=_now())
            if step is not None:
                self.state.update(step=step, steps=steps)
            self._touch()
        if message:
            self.event(message)
        self.flush(force=True)

    def advance(self, n: int = 1) -> None:
        with self._lock:
            self.state["done"] += n
            self._touch()

    def call_started(self) -> None:
        self.check_cancelled()
        with self._lock:
            self.state["calls"]["in_flight"] += 1
            self._touch()

    def call_finished(self, ok: bool, usage: dict[str, Any] | None) -> None:
        with self._lock:
            calls = self.state["calls"]
            calls["in_flight"] = max(0, calls["in_flight"] - 1)
            calls["finished" if ok else "failed"] += 1
            if usage:
                tokens = self.state["tokens"]
                tokens["prompt"] += int(usage.get("prompt_tokens") or 0)
                tokens["completion"] += int(usage.get("completion_tokens") or 0)
                details = usage.get("completion_tokens_details") or {}
                tokens["reasoning"] += int(details.get("reasoning_tokens") or 0)
            self._touch()

    def retry(self, reason: str) -> None:
        with self._lock:
            self.state["calls"]["retries"] += 1
        self.event(f"Retrying a model call: {reason}", "warn")

    # -- cancellation -----------------------------------------------------
    @property
    def cancelled(self) -> bool:
        return self._cancel.is_set()

    def check_cancelled(self) -> None:
        if self._cancel.is_set():
            raise JobCancelled("Cancelled by user")

    def close(self) -> None:
        release(self.job_id)

    # -- persistence (job thread only) -----------------------------------
    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            snap = {**self.state, "calls": dict(self.state["calls"]), "tokens": dict(self.state["tokens"])}
            snap["events"] = list(self._events)
        snap["elapsed_seconds"] = round(time.monotonic() - self._t0)
        return snap

    def flush(self, force: bool = False) -> None:
        if self._flush is None:
            return
        now = time.monotonic()
        if force or now - self._last_flush >= TICK_SECONDS:
            self._last_flush = now
            self._flush(self.snapshot())


class TrackedClient:
    """Wraps an LLM client: counts calls/tokens/retries, honours cancellation, logs timing."""

    def __init__(self, inner, tracker: JobTracker):
        self.inner = inner
        self.tracker = tracker
        self.model_name = inner.model_name
        if hasattr(inner, "on_retry"):
            inner.on_retry = tracker.retry

    def chat_json(self, *, label: str | None = None, **kwargs):
        self.tracker.call_started()
        started = time.monotonic()
        ok = False
        try:
            result = self.inner.chat_json(**kwargs)
            ok = True
            return result
        finally:
            usage = getattr(self.inner, "last_usage", None)
            self.tracker.call_finished(ok, usage() if callable(usage) else usage)
            seconds = time.monotonic() - started
            if label:
                if ok:
                    self.tracker.event(f"{label} finished in {seconds:.0f}s")
                elif not self.tracker.cancelled:
                    self.tracker.event(f"{label} failed after {seconds:.0f}s", "warn")


def run_parallel(
    fn: Callable[[T], R], items: Iterable[T], max_workers: int, tracker: JobTracker,
) -> Iterator[R]:
    """Run fn over items concurrently; yield results as they complete while flushing progress."""
    items = list(items)
    if not items:
        return
    pool = ThreadPoolExecutor(max_workers=min(max_workers, len(items)), thread_name_prefix="audience-agent")
    pending = {pool.submit(fn, item) for item in items}
    try:
        while pending:
            done, pending = wait(pending, timeout=TICK_SECONDS, return_when=FIRST_COMPLETED)
            for future in done:
                yield future.result()
            tracker.flush()
    finally:
        # On error/cancel do not block on calls already in flight; queued ones are dropped.
        pool.shutdown(wait=not pending, cancel_futures=True)


def call_one(fn: Callable[[], R], tracker: JobTracker) -> R:
    """Run a single blocking call off-thread so progress keeps flushing while it waits."""
    results = run_parallel(lambda _: fn(), [None], 1, tracker)
    try:
        return next(results)
    finally:
        results.close()
