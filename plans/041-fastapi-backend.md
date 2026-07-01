# Plan 041: FastAPI backend — feature-based structure, serve frontend

> **Executor instructions**: Follow this plan step by step. Run every verification command and confirm the expected result before moving to the next step. If anything in the "STOP conditions" section occurs, stop and report — do not improvise. When done, update the status row for this plan in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat bf83142..HEAD -- src/haxjobs/server/ src/haxjobs/api_server.py pyproject.toml`
> If `src/haxjobs/` doesn't exist, plan 040 must be executed first. STOP.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: LOW (adds FastAPI, old api_server.py stays as reference)
- **Depends on**: 040
- **Category**: migration
- **Planned at**: commit `bf83142`, 2026-06-30

## Why this matters

`api_server.py` is a 400-line stdlib `http.server` with manual route matching. FastAPI gives auto-generated OpenAPI docs at `/docs`, Pydantic validation, async support, and proper route organization.

The backend uses a **feature-based structure**: every business domain gets its own directory with `routes.py`, `service.py`, and `schemas.py`. Shared infrastructure (`db/`, `discovery/scrapers/`, `evaluate/`, `packs_builder/`) stays flat outside features. This keeps API code close to the domain it serves instead of scattered across `server/routes/`.

## Current state

- `src/haxjobs/api_server.py` — old stdlib HTTP server (stays, not deleted)
- `src/haxjobs/server/routes/` — old route handler modules
- DB modules at `src/haxjobs/db/`
- No FastAPI, no Pydantic models for request/response

## Target structure

```
src/haxjobs/
  app.py                          # FastAPI app + route mounting + static files
  cli.py                          # argparse CLI (already from plan 040)
  config.py                       # TOML config parser
  db/                             # shared data layer (flat, no ORM)
    schema.py, jobs.py, discovered_jobs.py, evaluations.py, decisions.py
  discovery/                      # scraper engines (infrastructure, not API)
    scrapers/ (greenhouse.py, ashby.py, lever.py, orchestrator.py)
    normalize.py, hooks.py, profile_search.py
  evaluate/                       # evaluation engine (infrastructure)
    common.py, run.py, api.py     # (api.py = direct LLM, added in plan 046)
  packs_builder/                  # pack generation (infrastructure)
    job_pack.py, ...
  features/                       # ← NEW: API layer, one dir per domain
    jobs/
      routes.py                   # FastAPI routes: GET /api/jobs, GET /api/jobs/:id
      schemas.py                  # Pydantic models: JobResponse, JobListParams
      service.py                  # Business logic: calls db/jobs.py, db/evaluations.py
    onboarding/
      routes.py                   # POST /api/onboarding/upload, /wizard, /complete
      schemas.py
      service.py                  # CV extraction, wizard question generation
    discovery/
      routes.py                   # POST /api/discovery/run, GET /status, GET /jobs/new
      schemas.py
      service.py                  # calls discovery/scrapers/orchestrator.py
    evaluation/
      routes.py                   # POST /api/evaluation/run, GET /status
      schemas.py
      service.py                  # calls evaluate/run.py
    decisions/
      routes.py                   # POST /api/jobs/:id/decision, GET /decisions
      schemas.py
      service.py                  # calls db/decisions.py
    packs/
      routes.py                   # POST /api/jobs/:id/pack, GET /pack/files
      schemas.py
      service.py                  # calls packs_builder/job_pack.py
    profile/
      routes.py                   # GET /api/profile, PUT /api/profile
      schemas.py
      service.py                  # reads/writes ~/.haxjobs/profile.json
  server/
    main.py                       # uvicorn runner
```

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Add deps | `uv add fastapi "uvicorn[standard]"` | exit 0 |
| Run tests | `uv run pytest -q tests/` | 255 passed |
| Start server | `uv run haxjobs start` | "Uvicorn running on http://127.0.0.1:8241" |
| Health check | `curl -s http://localhost:8241/api/health` | `{"status":"ok"}` |
| API docs | `curl -s -o /dev/null -w "%{http_code}" http://localhost:8241/docs` | 200 |
| Verify routes | `curl -s http://localhost:8241/openapi.json \| uv run python -c "import json,sys; d=json.load(sys.stdin); print(len(d['paths']))"` | > 1 |

## Scope

**In scope**:
- Create `src/haxjobs/app.py` — FastAPI app with CORS, static file serving, route mounting
- Create `src/haxjobs/server/main.py` — uvicorn runner
- Create `src/haxjobs/features/` directory with all 7 feature modules
- Each feature gets: `routes.py` (FastAPI router), `schemas.py` (Pydantic models), `service.py` (business logic)
- Health endpoint at `/api/health`
- Wire `haxjobs start` to launch uvicorn and open browser
- Serve React frontend from `../frontend/dist/` (when built by plan 042)

**Out of scope**:
- Full implementation of every route handler — just the skeleton + health endpoint. Full logic in plans 043-051.
- Deleting `api_server.py` — it stays as reference
- Deleting `server/routes/` — old route files stay until their logic migrates to features/
- `features/onboarding/` full logic — plan 043
- `features/discovery/` full logic — plan 045
- `features/evaluation/` full logic — plan 046
- `features/jobs/` full logic — plan 047

## Git workflow

- Commit: `git commit -m "add FastAPI backend with feature-based structure"`
- Do NOT push

## Steps

### Step 1: Add FastAPI dependency

```bash
uv add fastapi "uvicorn[standard]"
```

**Verify**: `grep fastapi pyproject.toml` → shows dependency. `uv run python -c "import fastapi; print(fastapi.__version__)"` → prints version.

### Step 2: Create FastAPI app

Create `src/haxjobs/app.py`:

```python
"""FastAPI application."""
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="HaxJobs", version="1.0.0")

# CORS for Vite dev server
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
    """Mount all feature routers. Called at startup so import errors are isolated."""
    from haxjobs.features.jobs.routes import router as jobs_router
    from haxjobs.features.onboarding.routes import router as onboarding_router
    from haxjobs.features.discovery.routes import router as discovery_router
    from haxjobs.features.evaluation.routes import router as evaluation_router
    from haxjobs.features.decisions.routes import router as decisions_router
    from haxjobs.features.packs.routes import router as packs_router
    from haxjobs.features.profile.routes import router as profile_router

    app.include_router(jobs_router, prefix="/api")
    app.include_router(onboarding_router, prefix="/api")
    app.include_router(discovery_router, prefix="/api")
    app.include_router(evaluation_router, prefix="/api")
    app.include_router(decisions_router, prefix="/api")
    app.include_router(packs_router, prefix="/api")
    app.include_router(profile_router, prefix="/api")


mount_features()

# Serve React frontend if built
_FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="frontend")
```

**Verify**: `uv run python -c "from haxjobs.app import app; print(app.title)"` → `HaxJobs`

### Step 3: Create feature directory skeleton

Create each feature with minimal skeleton:

```
src/haxjobs/features/
  __init__.py   (empty)
  jobs/
    __init__.py (empty)
    routes.py   (see below)
    schemas.py  (see below)
    service.py  (see below)
  onboarding/  __init__.py, routes.py, schemas.py, service.py
  discovery/   __init__.py, routes.py, schemas.py, service.py
  evaluation/  __init__.py, routes.py, schemas.py, service.py
  decisions/   __init__.py, routes.py, schemas.py, service.py
  packs/       __init__.py, routes.py, schemas.py, service.py
  profile/     __init__.py, routes.py, schemas.py, service.py
```

Template for each `routes.py`:
```python
"""<Feature> API routes."""
from fastapi import APIRouter

router = APIRouter(tags=["<feature>"])


@router.get("/<resource>")
def list_<resource>():
    return {"message": "not implemented", "feature": "<feature>"}
```

Template for each `schemas.py`:
```python
"""<Feature> request/response schemas."""
from pydantic import BaseModel


class <Resource>Response(BaseModel):
    id: int
    name: str
```

Template for each `service.py`:
```python
"""<Feature> business logic.

ponytail: thin wrappers over db/ modules and infrastructure.
Replaced with real logic in later plans.
"""

def list_<resource>():
    return []  # placeholder
```

For `features/jobs/` specifically, wire the existing DB functions since they already work:

```python
# features/jobs/service.py
from haxjobs.db.jobs import list_jobs as db_list_jobs
from haxjobs.db.evaluations import get_evaluation_for_job

def list_jobs(status_filter: str | None = None, offset: int = 0, limit: int | None = None):
    return db_list_jobs(status_filter=status_filter, offset=offset, limit=limit)
```

```python
# features/jobs/routes.py
from fastapi import APIRouter, Query
from .service import list_jobs
from .schemas import JobListResponse

router = APIRouter(tags=["jobs"])

@router.get("/jobs")
def get_jobs(
    status: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int | None = Query(None, ge=1, le=100),
):
    rows = list_jobs(status_filter=status, offset=offset, limit=limit)
    return {"jobs": rows, "total": len(rows)}
```

```python
# features/jobs/schemas.py
from pydantic import BaseModel


class JobResponse(BaseModel):
    id: int
    title: str
    company: str | None = None
    location: str | None = None
    status: str = "pending"
    source: str | None = None
    discovered_at: str | None = None
    role_family: str | None = None
    fit_score: int | None = None
    fit_level: int | None = None
```

**Verify**: `find src/haxjobs/features -name "*.py" | wc -l` → at least 22 Python files (7 dirs × 3 + 1 init)

### Step 4: Create uvicorn runner

Create `src/haxjobs/server/main.py`:

```python
"""Run the FastAPI server."""
import webbrowser
import threading
import uvicorn

def run(host: str = "127.0.0.1", port: int = 8241, open_browser: bool = True):
    if open_browser:
        threading.Timer(1.0, lambda: webbrowser.open(f"http://{host}:{port}")).start()
    uvicorn.run("haxjobs.app:app", host=host, port=port, reload=False)

if __name__ == "__main__":
    run()
```

Update `cli.py` `cmd_start()` to accept `--no-browser`:

```python
def cmd_start(args):
    from haxjobs.server.main import run
    run(host=args.host, port=args.port, open_browser=not args.no_browser)

# In argparse setup:
start.add_argument("--no-browser", action="store_true", help="Don't open browser")
```

**Verify**: `uv run haxjobs start --no-browser & sleep 2 && curl -s http://localhost:8241/api/health && kill %1` → `{"status":"ok","version":"1.0.0"}`

### Step 5: Run tests and verify

```bash
uv run pytest -q tests/
```

**Verify**: 255 passed. The FastAPI app shouldn't break existing tests since they don't import it.

Manual verification:
```bash
# Start server in background
uv run haxjobs start --no-browser &
sleep 2

# Health
curl -s http://localhost:8241/api/health

# API docs
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8241/docs

# Jobs endpoint (should work since it's wired)
curl -s http://localhost:8241/api/jobs | head -c 200

kill %1
```

**Verify**: health returns ok, docs returns 200, jobs returns JSON

### Step 6: Commit

```bash
git add -A && git commit -m "add FastAPI backend with feature-based structure"
```

## Done criteria

- [ ] `fastapi` and `uvicorn` in pyproject.toml deps
- [ ] `uv run haxjobs start` starts server on :8241
- [ ] `curl http://localhost:8241/api/health` → `{"status":"ok","version":"1.0.0"}`
- [ ] `curl http://localhost:8241/docs` → 200
- [ ] `curl http://localhost:8241/api/jobs` → JSON response
- [ ] `features/` directory has 7 feature modules, each with routes/schemas/service
- [ ] `app.py` mounts all 7 routers
- [ ] 255 tests pass
- [ ] Old `api_server.py` still exists (not deleted)

## STOP conditions

Stop if:

- `uv add fastapi` fails — check pyproject.toml from plan 040 exists
- Port 8241 already in use — `lsof -i :8241`, kill the process
- Any feature router import causes a crash — it's likely an old `server/routes/` file with stale imports. Fix the import or stub the router.
- `uvicorn` can't find `haxjobs.app:app` — make sure `PYTHONPATH` includes `src/`. uv run should handle this.

## Maintenance notes

- `features/jobs/` is the only feature with real DB calls in this plan. All others have placeholder returns. Real logic in plans 043-051.
- The old `server/routes/` directory stays until all its logic is migrated to features. Delete it in a cleanup plan after all features are built.
- `mount_features()` is called at import time. If any feature module has broken imports, it will crash the app. During development, consider wrapping each import in try/except.
- CORS allows `localhost:5173` (Vite dev server) and `localhost:8241` (production). Add more origins as needed.
