from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.analysis import router as analysis_router
from app.api.routes.demo import router as demo_router
from app.api.routes.health import router as health_router
from app.api.routes.profile import router as profile_router
from app.core.config import Settings


def build_app(settings: Settings) -> FastAPI:
    app = FastAPI(title=settings.project_name, version=settings.project_version)
    app.state.settings = settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(analysis_router)
    app.include_router(demo_router)
    app.include_router(profile_router)
    return app
