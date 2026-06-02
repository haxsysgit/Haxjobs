from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from haxjobs_api.api.health import router as health_router
from haxjobs_api.config import get_settings
from haxjobs_api.features.jobs.router import router as jobs_router
from haxjobs_api.features.packs.router import router as packs_router
from haxjobs_api.features.documents.router import router as documents_router
from haxjobs_api.features.profiles.router import router as profiles_router
from haxjobs_api.features.tasks.router import router as tasks_router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="HaxJobs API")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1):5173",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    def read_root():
        return {
            "service": settings.app_name,
            "status": "ok",
            "ui_hint": f"Use the HaxJobs frontend on {settings.frontend_origin} for the main workflow.",
            "docs_path": "/docs",
            "health_path": "/health",
        }

    app.include_router(health_router)
    app.include_router(jobs_router)
    app.include_router(packs_router)
    app.include_router(documents_router)
    app.include_router(profiles_router)
    app.include_router(tasks_router)
    return app


app = create_app()
