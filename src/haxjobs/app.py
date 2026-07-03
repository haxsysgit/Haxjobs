"""FastAPI application."""
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    from haxjobs.db.schema import init
    init()
    yield


app = FastAPI(title="HaxJobs", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8241"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


def mount_features():
    """Mount all feature routers. Called at import time so import errors surface early."""
    from haxjobs.features.jobs.routes import router as jobs_router
    from haxjobs.features.onboarding.routes import router as onboarding_router
    from haxjobs.features.discovery.routes import router as discovery_router
    from haxjobs.features.evaluation.routes import router as evaluation_router
    from haxjobs.features.decisions.routes import router as decisions_router
    from haxjobs.features.packs.routes import router as packs_router
    from haxjobs.features.profile.routes import router as profile_router
    from haxjobs.features.setup.routes import router as setup_router

    app.include_router(jobs_router, prefix="/api")
    app.include_router(onboarding_router, prefix="/api")
    app.include_router(discovery_router, prefix="/api")
    app.include_router(evaluation_router, prefix="/api")
    app.include_router(decisions_router, prefix="/api")
    app.include_router(packs_router, prefix="/api")
    app.include_router(profile_router, prefix="/api")
    app.include_router(setup_router, prefix="/api")


mount_features()

_FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if _FRONTEND_DIR.exists():
    # Serve static assets (JS, CSS, fonts, images, favicon)
    assets = _FRONTEND_DIR / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=str(assets)), name="assets")
    # Serve favicon
    favicon = _FRONTEND_DIR / "favicon.svg"
    if favicon.exists():
        @app.get("/favicon.svg", include_in_schema=False)
        def favicon():
            return FileResponse(favicon)
    # SPA catch-all — serve index.html for all client-side routes
    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str, request: Request):
        # Skip API routes — they're already matched above
        if full_path.startswith("api/"):
            return FileResponse(_FRONTEND_DIR / "404.html") if (_FRONTEND_DIR / "404.html").exists() else {"detail": "Not Found"}
        return FileResponse(_FRONTEND_DIR / "index.html")
