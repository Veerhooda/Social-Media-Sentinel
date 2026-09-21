from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class JobRunStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PASS = "PASS"
    FAIL = "FAIL"
    SKIPPED = "SKIPPED"


class JobExecutionResult(BaseModel):
    status: JobRunStatus = JobRunStatus.PASS
    processed_count: int = Field(default=0, ge=0)
    detail: str | None = None


class JobStatus(BaseModel):
    name: str
    interval_seconds: float = Field(gt=0)
    status: JobRunStatus = JobRunStatus.PENDING
    last_started_at: datetime | None = None
    last_finished_at: datetime | None = None
    next_run_at: datetime | None = None
    processed_count: int = Field(default=0, ge=0)
    total_processed_count: int = Field(default=0, ge=0)
    duration_ms: float | None = Field(default=None, ge=0)
    error: str | None = None
    detail: str | None = None
    run_count: int = Field(default=0, ge=0)
    overlap_skips: int = Field(default=0, ge=0)


class SchedulerStatus(BaseModel):
    enabled: bool
    running: bool
    started_at: datetime | None = None
    stopped_at: datetime | None = None
    jobs: list[JobStatus]
