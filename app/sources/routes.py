"""Collection sources CRUD and manual job runs."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.scheduler.schemas import JobStatus
from app.sources.jobs import (
    TELEGRAM_COLLECTION_JOB,
    X_COLLECTION_JOB,
    YOUTUBE_COLLECTION_JOB,
)
from app.sources.repository import SourceRepository
from app.sources.schemas import (
    PlatformCollector,
    SourceCreate,
    SourceOut,
    SourcePlatform,
    SourcesOverview,
    SourceUpdate,
)

router = APIRouter(prefix="/api", tags=["sources"])

JOBS = {
    SourcePlatform.X: X_COLLECTION_JOB,
    SourcePlatform.TELEGRAM: TELEGRAM_COLLECTION_JOB,
    SourcePlatform.YOUTUBE: YOUTUBE_COLLECTION_JOB,
}


def _credentials(settings: Settings, platform: SourcePlatform) -> tuple[bool, str]:
    if platform is SourcePlatform.X:
        ok = bool(settings.x_bearer_token)
        return ok, "X_BEARER_TOKEN configured" if ok else "X_BEARER_TOKEN is not set in .env"
    if platform is SourcePlatform.TELEGRAM:
        ok = bool(settings.telegram_api_id and settings.telegram_api_hash and settings.telegram_session_string)
        return ok, "Telegram API id, hash and session configured" if ok else "TELEGRAM_API_ID / API_HASH / SESSION_STRING missing in .env"
    ok = bool(settings.youtube_api_key)
    return ok, "YOUTUBE_API_KEY configured" if ok else "YOUTUBE_API_KEY is not set in .env"


@router.get("/sources", response_model=SourcesOverview)
def list_sources(request: Request, session: Session = Depends(get_db_session), settings: Settings = Depends(get_settings)) -> SourcesOverview:
    repo = SourceRepository(session)
    repo.seed_from_settings(settings)
    scheduler = getattr(request.app.state, "scheduler", None)
    snapshot = scheduler.snapshot() if scheduler else None
    intervals = {job.name: job.interval_seconds for job in snapshot.jobs} if snapshot else {}
    platforms = []
    for platform in SourcePlatform:
        ok, detail = _credentials(settings, platform)
        platforms.append(PlatformCollector(
            platform=platform, credentials_configured=ok, credential_detail=detail,
            job_name=JOBS[platform], interval_seconds=intervals.get(JOBS[platform], 0) or 1,
            sources=[SourceOut.model_validate(row) for row in repo.list(platform)],
        ))
    return SourcesOverview(
        scheduler_enabled=bool(snapshot and snapshot.enabled),
        scheduler_running=bool(snapshot and snapshot.running),
        platforms=platforms,
    )


@router.post("/sources", response_model=SourceOut, status_code=status.HTTP_201_CREATED)
def add_source(body: SourceCreate, session: Session = Depends(get_db_session)) -> SourceOut:
    return SourceOut.model_validate(SourceRepository(session).add(body.platform, body.target, body.label))


@router.patch("/sources/{source_id}", response_model=SourceOut)
def update_source(source_id: UUID, body: SourceUpdate, session: Session = Depends(get_db_session)) -> SourceOut:
    repo = SourceRepository(session)
    row = repo.get(source_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Source not found")
    if body.enabled is not None:
        row.enabled = body.enabled
    if body.label is not None:
        row.label = body.label or None
    session.commit()
    return SourceOut.model_validate(row)


@router.delete("/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source(source_id: UUID, session: Session = Depends(get_db_session)) -> Response:
    repo = SourceRepository(session)
    row = repo.get(source_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Source not found")
    repo.delete(row)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/system/jobs/{name}/run", response_model=JobStatus)
def run_job(name: str, request: Request) -> JobStatus:
    """Run one registered job now (works with the scheduler loop disabled). Blocks until done."""
    scheduler = getattr(request.app.state, "scheduler", None)
    if scheduler is None:
        raise HTTPException(status_code=503, detail="Scheduler is not initialized")
    if name not in {job.name for job in scheduler.snapshot().jobs}:
        raise HTTPException(status_code=404, detail=f"Unknown job: {name}")
    status_before = scheduler.get_job_status(name)
    if status_before.status == "RUNNING":
        raise HTTPException(status_code=409, detail=f"{name} is already running")
    return scheduler.run_job_now(name)
