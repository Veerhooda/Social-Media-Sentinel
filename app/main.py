from __future__ import annotations

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.audience_lab.routes import router as audience_lab_router
from app.sources.routes import router as sources_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.scheduler.jobs import build_scheduler
from app.scheduler.service import SchedulerService


def create_app(
    *,
    scheduler: SchedulerService | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    configure_logging()
    settings = settings or get_settings()
    scheduler_service = scheduler or build_scheduler(settings)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        application.state.scheduler = scheduler_service
        scheduler_service.start()
        try:
            yield
        finally:
            scheduler_service.stop()

    application = FastAPI(
        title="Social Sentinel API",
        version="0.1.0",
        description="Canonical multi-platform social analytics API",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["*"],
    )
    application.include_router(router)
    application.include_router(audience_lab_router)
    application.include_router(sources_router)
    return application


app = create_app()


def run() -> None:
    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.api_host, port=settings.api_port, reload=False)
