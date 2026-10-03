"""HTTP API for the Audience Lab: /api/audience-lab/*"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.audience_lab.config import AudienceLabSettings, get_lab_settings
from app.audience_lab.llm import LLMClient, LLMError, build_client
from app.audience_lab.models import AudienceProfile, AudienceSegment, AudienceSegmentation, PostSimulation
from app.audience_lab.profiles import count_profiles, counts_by_source, sync_social_profiles, upsert_profiles
from app.audience_lab.schemas import (
    LabStatus,
    ProfileImport,
    ProfileOut,
    ProfilePage,
    SegmentationOut,
    SegmentationRequest,
    SegmentOut,
    SimulationOut,
    SimulationRequest,
    SimulationSummary,
    UpsertResult,
)
from app.audience_lab.segmentation import run_segmentation
from app.audience_lab.tracker import is_live, register, release, request_cancel
from app.audience_lab.simulation import media_meta, run_simulation
from app.db.session import SessionLocal, get_db_session

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/audience-lab", tags=["audience-lab"])
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="audience-lab-job")


# -- injectable dependencies (overridden in tests) ----------------------------

def get_session_factory() -> sessionmaker[Session]:
    return SessionLocal


def get_client_factory() -> Callable[[AudienceLabSettings], LLMClient]:
    return build_client


def get_job_runner() -> Callable[[Callable[[], None]], None]:
    return lambda job: _executor.submit(job).add_done_callback(_log_crash)


def _log_crash(future) -> None:
    if future.exception() is not None:
        log.error("Audience Lab job crashed", exc_info=future.exception())


ACTIVE = ("QUEUED", "RUNNING")


def _job_id(row) -> UUID:
    return row.segmentation_id if isinstance(row, AudienceSegmentation) else row.simulation_id


def _expire_if_stale(session: Session, row, settings: AudienceLabSettings) -> None:
    """Fail jobs that can no longer finish: not owned by this server process, or silent for too long."""
    if row.status not in ACTIVE:
        return
    if not is_live(_job_id(row)):
        row.status = "FAILED"
        row.error = "The server restarted while this job was running. Start it again."
        row.completed_at = datetime.now(UTC)
        session.commit()
        return
    last = (row.progress or {}).get("last_activity_at")
    try:
        seen = datetime.fromisoformat(last) if last else row.created_at
    except ValueError:
        seen = row.created_at
    limit = timedelta(seconds=settings.audience_lab_timeout_seconds * (settings.audience_lab_max_retries + 1) + 120)
    if seen and datetime.now(UTC) - seen > limit:
        row.status = "FAILED"
        row.error = "No progress for too long; the job was interrupted (server restart or crash). Start it again."
        row.completed_at = datetime.now(UTC)
        session.commit()


def _guard(session: Session, model, job_id: UUID, fn: Callable[[], None]) -> None:
    """Never leave a job RUNNING after an unexpected crash."""
    try:
        fn()
    except Exception as exc:  # noqa: BLE001 - surfaced on the job row and logged
        log.exception("Audience Lab job %s crashed", job_id)
        session.rollback()
        row = session.get(model, job_id)
        if row is not None and row.status in ACTIVE:
            row.status = "FAILED"
            row.error = f"Internal error: {type(exc).__name__}: {str(exc)[:500]}"
            row.completed_at = datetime.now(UTC)
            session.commit()
    finally:
        release(job_id)


def _client_or_503(factory, settings: AudienceLabSettings) -> LLMClient:
    try:
        return factory(settings)
    except LLMError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


# -- status & profiles ---------------------------------------------------------

@router.get("/status", response_model=LabStatus)
def lab_status(session: Session = Depends(get_db_session), settings: AudienceLabSettings = Depends(get_lab_settings)) -> LabStatus:
    latest = session.scalar(
        select(AudienceSegmentation.segmentation_id).where(AudienceSegmentation.status == "COMPLETED")
        .order_by(AudienceSegmentation.created_at.desc()).limit(1)
    )
    platforms = [p for p in session.scalars(
        select(AudienceProfile.platform).where(AudienceProfile.platform.is_not(None))
        .group_by(AudienceProfile.platform).order_by(func.count().desc())
    )]
    return LabStatus(
        model_name=settings.audience_lab_model, api_configured=bool(settings.api_key),
        base_url=settings.meta_model_base_url, total_profiles=count_profiles(session),
        by_source=counts_by_source(session), latest_segmentation_id=latest, platforms=platforms,
    )


@router.post("/profiles/sync", response_model=UpsertResult)
def sync_profiles(session: Session = Depends(get_db_session)) -> UpsertResult:
    """Refresh profiles collected from stored social accounts (idempotent upsert)."""
    return sync_social_profiles(session)


@router.post("/profiles/import", response_model=UpsertResult)
def import_profiles(body: ProfileImport, session: Session = Depends(get_db_session)) -> UpsertResult:
    """Add or update audience records from any source (CRM, survey, manual personas …)."""
    return upsert_profiles(session, body.profiles)


@router.get("/profiles", response_model=ProfilePage)
def list_profiles(
    source: str | None = None, limit: int = Query(default=50, ge=1, le=500), offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db_session),
) -> ProfilePage:
    query = select(AudienceProfile)
    count = select(func.count()).select_from(AudienceProfile)
    if source:
        query, count = query.where(AudienceProfile.source == source), count.where(AudienceProfile.source == source)
    rows = session.scalars(query.order_by(AudienceProfile.updated_at.desc()).limit(limit).offset(offset))
    return ProfilePage(total=session.scalar(count) or 0, items=[ProfileOut.model_validate(r, from_attributes=True) for r in rows])


# -- segmentation --------------------------------------------------------------

def _segmentation_out(session: Session, run: AudienceSegmentation, settings: AudienceLabSettings | None = None) -> SegmentationOut:
    if settings is not None:
        _expire_if_stale(session, run, settings)
    segments = session.scalars(
        select(AudienceSegment).where(AudienceSegment.segmentation_id == run.segmentation_id)
        .order_by(AudienceSegment.share.desc())
    )
    out = SegmentationOut.model_validate(run, from_attributes=True)
    out.segments = [SegmentOut.model_validate(s, from_attributes=True) for s in segments]
    return out


@router.post("/segmentations", response_model=SegmentationOut, status_code=status.HTTP_202_ACCEPTED)
def create_segmentation(
    body: SegmentationRequest,
    session: Session = Depends(get_db_session),
    settings: AudienceLabSettings = Depends(get_lab_settings),
    factory=Depends(get_session_factory),
    client_factory=Depends(get_client_factory),
    runner=Depends(get_job_runner),
) -> SegmentationOut:
    client = _client_or_503(client_factory, settings)
    if count_profiles(session) == 0:
        sync_social_profiles(session)
    run = AudienceSegmentation(status="QUEUED", model_name=client.model_name, params=body.model_dump(), progress={"stage": "queued"})
    session.add(run)
    session.commit()
    run_id = run.segmentation_id

    def job() -> None:
        with factory() as job_session:
            _guard(job_session, AudienceSegmentation, run_id, lambda: run_segmentation(job_session, run_id, body, client, settings))

    register(run_id)
    runner(job)
    session.refresh(run)
    return _segmentation_out(session, run)


@router.get("/segmentations", response_model=list[SegmentationOut])
def list_segmentations(
    limit: int = Query(default=20, ge=1, le=100), session: Session = Depends(get_db_session),
    settings: AudienceLabSettings = Depends(get_lab_settings),
) -> list[SegmentationOut]:
    runs = session.scalars(select(AudienceSegmentation).order_by(AudienceSegmentation.created_at.desc()).limit(limit))
    return [_segmentation_out(session, run, settings) for run in runs]


@router.get("/segmentations/{segmentation_id}", response_model=SegmentationOut)
def get_segmentation(
    segmentation_id: UUID, session: Session = Depends(get_db_session),
    settings: AudienceLabSettings = Depends(get_lab_settings),
) -> SegmentationOut:
    run = session.get(AudienceSegmentation, segmentation_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Segmentation not found")
    return _segmentation_out(session, run, settings)


@router.post("/segmentations/{segmentation_id}/cancel", response_model=SegmentationOut)
def cancel_segmentation(segmentation_id: UUID, session: Session = Depends(get_db_session)) -> SegmentationOut:
    run = session.get(AudienceSegmentation, segmentation_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Segmentation not found")
    _cancel(session, run, run.segmentation_id)
    return _segmentation_out(session, run)


def _cancel(session: Session, row, job_id: UUID) -> None:
    if row.status not in ACTIVE:
        return
    if not request_cancel(job_id):  # job thread is gone (e.g. after a restart)
        row.status = "CANCELLED"
        row.error = "Cancelled by user"
        row.completed_at = datetime.now(UTC)
        session.commit()
    else:
        row.progress = {**(row.progress or {}), "cancel_requested": True}
        session.commit()


# -- post simulations ----------------------------------------------------------

@router.post("/simulations", response_model=SimulationOut, status_code=status.HTTP_202_ACCEPTED)
def create_simulation(
    body: SimulationRequest,
    session: Session = Depends(get_db_session),
    settings: AudienceLabSettings = Depends(get_lab_settings),
    factory=Depends(get_session_factory),
    client_factory=Depends(get_client_factory),
    runner=Depends(get_job_runner),
) -> SimulationOut:
    if body.image_data_url and len(body.image_data_url) * 3 // 4 > settings.audience_lab_max_image_bytes:
        raise HTTPException(status_code=413, detail="Image is too large")
    if body.segmentation_id:
        run = session.get(AudienceSegmentation, body.segmentation_id)
    else:
        run = session.scalars(
            select(AudienceSegmentation).where(AudienceSegmentation.status == "COMPLETED")
            .order_by(AudienceSegmentation.created_at.desc()).limit(1)
        ).first()
    if run is None or run.status != "COMPLETED":
        raise HTTPException(status_code=409, detail="Build audience segments first (no completed segmentation found)")
    client = _client_or_503(client_factory, settings)
    sim = PostSimulation(
        segmentation_id=run.segmentation_id, status="QUEUED", model_name=client.model_name,
        platform=body.platform, post_text=body.text, media=media_meta(body), progress={"stage": "queued"},
    )
    session.add(sim)
    session.commit()
    sim_id = sim.simulation_id

    def job() -> None:
        with factory() as job_session:
            _guard(job_session, PostSimulation, sim_id, lambda: run_simulation(job_session, sim_id, body, client, settings))

    register(sim_id)
    runner(job)
    session.refresh(sim)
    return SimulationOut.model_validate(sim, from_attributes=True)


@router.get("/simulations", response_model=list[SimulationSummary])
def list_simulations(limit: int = Query(default=20, ge=1, le=100), session: Session = Depends(get_db_session)) -> list[SimulationSummary]:
    sims = session.scalars(select(PostSimulation).order_by(PostSimulation.created_at.desc()).limit(limit))
    return [
        SimulationSummary(
            simulation_id=s.simulation_id, status=s.status, platform=s.platform, post_text=s.post_text[:280],
            created_at=s.created_at, headline=(s.analysis or {}).get("headline"),
        )
        for s in sims
    ]


@router.get("/simulations/{simulation_id}", response_model=SimulationOut)
def get_simulation(
    simulation_id: UUID, session: Session = Depends(get_db_session),
    settings: AudienceLabSettings = Depends(get_lab_settings),
) -> SimulationOut:
    sim = session.get(PostSimulation, simulation_id)
    if sim is None:
        raise HTTPException(status_code=404, detail="Simulation not found")
    _expire_if_stale(session, sim, settings)
    return SimulationOut.model_validate(sim, from_attributes=True)


@router.post("/simulations/{simulation_id}/cancel", response_model=SimulationOut)
def cancel_simulation(simulation_id: UUID, session: Session = Depends(get_db_session)) -> SimulationOut:
    sim = session.get(PostSimulation, simulation_id)
    if sim is None:
        raise HTTPException(status_code=404, detail="Simulation not found")
    _cancel(session, sim, sim.simulation_id)
    return SimulationOut.model_validate(sim, from_attributes=True)
