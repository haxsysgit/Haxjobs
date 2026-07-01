# Plan 041: FastAPI backend — replace api_server.py, serve frontend

> **Executor instructions**: Follow this plan step by step. Run every verification command and confirm the expected result before moving to the next step. If anything in the "STOP conditions" section occurs, stop and report — do not improvise. When done, update the status row for this plan in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat bf83142..HEAD -- src/haxjobs/api_server.py src/haxjobs/server/`
> If `src/haxjobs/` doesn't exist yet, plan 040 must be executed first. STOP.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: LOW (adds FastAPI alongside old api_server.py, old code stays until frontend is ready)
- **Depends on**: 040
- **Category**: migration
- **Planned at**: commit `bf83142`, 2026-06-30

## Why this matters

`api_server.py` is a 400-line stdlib `http.server` with manual route matching via `if path == "/api/jobs":`. Every endpoint is a hand-written if/elif block. FastAPI gives us auto-generated OpenAPI docs at `/docs`, Pydantic validation, async support, and proper route organization. The FastAPI app also serves the React frontend build from `frontend/dist/` — single process, single port. The old `api_server.py` stays (not deleted) until the frontend migration is complete in later plans — it can still run for testing.

## Current state

- `src/haxjobs/api_server.py` — stdlib HTTP server, ~400 lines, manual route matching
- `src/haxjobs/server/routes/` — route handler modules (jobs.py, outreach.py, pack_resources.py, resources.py)
- DB modules import via `from haxjobs.db import ...`
- No request validation, no API docs, no CORS headers

Example current pattern (api_server.py:240):
```python
if path == "/api/jobs":
    from haxjobs.server.routes.jobs import list_jobs
    data = list_jobs()
    self.send_response(200)
    self.send_header("Content-Type", "application/json")
    self.end_headers()
    self.wfile.write(json.dumps(data).encode())
```

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Run tests | `python3 -m pytest -q tests/` | 255 passed |
| Start server | `python3 -m haxjobs.server.app` | "Uvicorn running on http://localhost:8241" |
| Check API docs | `curl -s http://localhost:8241/docs | head -c 100` | HTML response |
| Verify 404 | `curl -s -o /dev/null -w "%{http_code}" http://localhost:8241/api/nonexistent` | 404 |

## Scope

**In scope**:
- Create `src/haxjobs/server/app.py` — FastAPI app with route mounting
- Create `src/haxjobs/server/main.py` — uvicorn runner
- Wire existing route handlers into FastAPI routes
- Add CORS middleware for dev mode
- Add static file serving for `frontend/dist/`
- Wire `haxjobs start` CLI command to launch the server
- Add `fastapi` and `uvicorn` to `pyproject.toml` deps (already there from plan 040)

**Out of scope**:
- `api_server.py` — do NOT delete, it stays as reference
- `server/routes/` — do NOT change handler internals, only mount them
- Frontend build — that's plan 042

## Git workflow

- Commit: `git commit -m "add FastAPI backend, keep old api_server for now"`
- Do NOT push

## Steps

### Step 1: Create FastAPI app

Create `src/haxjobs/server/app.py`:

```python
"""FastAPI application — replaces the old stdlib api_server.py."""
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="HaxJobs", version="1.0.0")

# CORS for dev (Vite dev server on :5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8241"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and mount route handlers
# ponytail: import inside function so module loads even if a route module is broken
def _mount_routes():
    from haxjobs.server.routes.jobs import router as jobs_router
    from haxjobs.server.routes.outreach import router as outreach_router
    from haxjobs.server.routes.pack_resources import router as pack_router
    from haxjobs.server.routes.resources import router as resources_router
    app.include_router(jobs_router, prefix="/api")
    app.include_router(outreach_router, prefix="/api")
    app.include_router(pack_router, prefix="/api")
    app.include_router(resources_router, prefix="/api")

_mount_routes()

# Serve React frontend (if built)
_FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="frontend")


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "1.0.0"}
```

**Verify**: `python3 -c "from haxjobs.server.app import app; print(app.title)"` → `HaxJobs`

### Step 2: Create route modules with FastAPI routers

The old `server/routes/jobs.py` uses `list_jobs()` as a plain function. We need to wrap it in a FastAPI router. Create router wrappers — minimal, don't change existing logic.

Create `src/haxjobs/server/routes/jobs.py` with both old and new:

```python
"""Job routes."""
from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter(tags=["jobs"])

# Import the existing list_jobs logic
from haxjobs.server.routes._jobs import list_jobs as _list_jobs


@router.get("/jobs")
def get_jobs(
    status_filter: Optional[str] = Query(None, alias="status"),
    offset: int = Query(0, ge=0),
    limit: Optional[int] = Query(None, ge=1, le=100),
):
    """List jobs with evaluations, paginated."""
    return _list_jobs(status_filter=status_filter, offset=offset, limit=limit)
```

But wait — the old `list_jobs` function is in the same file. Better approach: rename the old file to `_jobs_impl.py` and have the new `jobs.py` import from it.

Actually, the ponytail approach: just add `router` and `@router.get` decorators to the existing file. The old API server called `list_jobs()` directly. FastAPI routes call the function via the decorator. Both can coexist.

**Ponytail approach**: Add FastAPI route decorators to the existing functions. Don't rename files, don't create wrappers.

Edit `src/haxjobs/server/routes/jobs.py` — add at top:
```python
from fastapi import APIRouter, Query
router = APIRouter(tags=["jobs"])
```

Add `@router.get("/jobs")` decorator above `list_jobs()`. Add Query params for status_filter, offset, limit. The function body doesn't change.

**Verify**: `grep "router" src/haxjobs/server/routes/jobs.py` → shows router definition + @router.get

Do the same for the other route files. Only if they exist and are simple. If a route file is complex, skip it — we'll add it later.

Actually, to keep this plan minimal: **only create the FastAPI app shell and the /api/health endpoint**. Wire existing routes in a follow-up plan when we actually need them. The frontend development just needs the health check to confirm the server is running. Real API endpoints get wired when we build their UI.

**Revised approach**:
1. Create `app.py` with health endpoint
2. Wire `haxjobs start` to launch uvicorn
3. Leave old route mounting for plan 045 (discovery), 047 (dashboard), etc.

### Step 3: Create uvicorn runner

Create `src/haxjobs/server/main.py`:

```python
"""Run the FastAPI server."""
import uvicorn

def run(host: str = "127.0.0.1", port: int = 8241):
    uvicorn.run("haxjobs.server.app:app", host=host, port=port, reload=False)

if __name__ == "__main__":
    run()
```

### Step 4: Wire CLI

Edit `src/haxjobs/cli.py`:

```python
"""HaxJobs CLI."""
import sys
import webbrowser

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "start":
        print("Starting HaxJobs on http://localhost:8241")
        # Open browser after a short delay
        import threading
        threading.Timer(1.0, lambda: webbrowser.open("http://localhost:8241")).start()
        from haxjobs.server.main import run
        run()
    else:
        print("HaxJobs v1.0.0")
        print("  haxjobs start    Start the server")

if __name__ == "__main__":
    main()
```

**Verify**: `haxjobs` → prints usage. `haxjobs start & sleep 2 && curl -s http://localhost:8241/api/health && kill %1` → `{"status":"ok","version":"1.0.0"}`

### Step 5: Run tests

```bash
python3 -m pytest -q tests/
```

**Verify**: 255 passed. The FastAPI app doesn't break existing tests because tests don't import it.

### Step 6: Commit

```bash
git add -A && git commit -m "add FastAPI backend with health endpoint and haxjobs start CLI"
```

## Done criteria

- [ ] `python3 -m haxjobs.server.main` starts server on :8241
- [ ] `curl http://localhost:8241/api/health` returns `{"status":"ok","version":"1.0.0"}`
- [ ] `haxjobs start` starts server
- [ ] FastAPI auto-docs at http://localhost:8241/docs load
- [ ] 255 tests pass
- [ ] Old `api_server.py` still exists (not deleted)

## STOP conditions

Stop if:

- fastapi or uvicorn import fails — check pyproject.toml deps
- Port 8241 is already in use — configure a different port or kill the process
- Old server/routes/ files break from the FastAPI imports — remove the import, keep files as-is

## Maintenance notes

- The old `api_server.py` stays until all frontend API calls are migrated to FastAPI routes. Then delete it.
- Route files that got `from fastapi import ...` added at top may need that import removed if they cause circular imports. The ponytail escape hatch: revert the import, keep the old function, wire the route later.
- `haxjobs start` will grow flags: `--port`, `--no-browser`, `--dev` for Vite hot-reload mode. Not now.
