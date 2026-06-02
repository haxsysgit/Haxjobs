# HaxJobs

HaxJobs is the UI, state, and workflow layer for a Hermes-powered job application pipeline.

Hermes does the heavy lifting: job analysis, fit scoring, profile-aware application-pack generation, contact discovery, outreach drafting, and approval-gated apply assistance. HaxJobs gives that pipeline a durable product surface: saved jobs, application status, profile facts, reusable answers, task queues, generated documents, notes, and review/approval screens.

Simple mental model:

```text
Hermes  = worker, reasoning engine, automation layer
HaxJobs = interface, database, dashboard, queue, approval surface
```

## Current status

The repo is in the `0.1.x` foundation line.

Implemented so far:

- `0.1.0` project skeleton
  - FastAPI backend
  - Vue 3 + Vite frontend created with `create-vue`
  - backend `/health` endpoint
  - frontend health check wired to the backend
- `0.1.1` database foundation
  - SQLAlchemy engine/session setup
  - SQLite local default
  - Alembic migration pipeline
  - initial baseline migration
  - local data/document placeholders
- `0.1.2` core data model
  - feature-based backend modules
  - SQLAlchemy 2.0 typed ORM models
  - Pydantic schemas beside feature models
  - Alembic migration for core HaxJobs tables

- `0.1.3` core CRUD APIs
  - manual job save endpoint
  - profile/fact/saved-answer endpoints
  - Hermes task creation endpoint
  - status event creation during manual job save

- `0.1.4` local document/profile fixture support
  - safe local document storage under `data/documents`
  - application-pack and document registration endpoints
  - private profile JSON import service/script
  - profile/account setup docs without storing passwords

Next planned slices live in `docs/ROADMAP.md` and `docs/roadmaps/`.

## Repository layout

```text
haxjobs/
  backend/
    haxjobs_api/
      api/              # FastAPI route modules
      config.py         # environment/settings
      database.py       # SQLAlchemy engine/session helpers
      main.py           # FastAPI app entrypoint
    alembic/            # database migrations
    tests/              # backend tests
  frontend/
    src/
      services/         # frontend API clients
      views/            # Vue route views
    package.json
  docs/
    ROADMAP.md
    roadmaps/
  scripts/
    dev.sh              # start/stop/restart/logs for local app
    dev-backend.sh
    dev-frontend.sh
  data/
    documents/          # local generated document storage placeholder
```

## Requirements

- Python 3.12+
- `uv`
- Node.js 20.19+ or 22.12+
- npm

On this machine, use `python3` rather than `python`.

## First-time setup

Install backend dependencies:

```bash
uv sync
```

Install frontend dependencies:

```bash
cd frontend
npm install
```

Create local database tables:

```bash
uv run alembic upgrade head
```

## Running locally

Recommended all-in-one dev manager:

```bash
./scripts/dev.sh start
./scripts/dev.sh logs
./scripts/dev.sh status
./scripts/dev.sh stop
```

Useful commands:

```bash
./scripts/dev.sh restart   # stop then start both servers
./scripts/dev.sh clean     # stop tracked/stale HaxJobs dev processes
./scripts/dev.sh logs api  # follow backend log only
./scripts/dev.sh logs web  # follow frontend log only
```

Manual backend:

```bash
uv run uvicorn haxjobs_api.main:app --app-dir backend --reload
```

Manual frontend:

```bash
cd frontend
npm run dev
```

Local document storage defaults to:

```text
data/documents
```

You can override it with:

```bash
HAXJOBS_DOCUMENT_STORAGE_DIR=data/documents
```

Import ignored local profile fixture data into the development database:

```bash
uv run python scripts/import-profile.py data/private/arinze_profile.local.json
```

The private fixture file stays ignored under `data/private/`.

Default local URLs:

```text
Backend:  http://localhost:8000
Health:   http://localhost:8000/health
Frontend: http://localhost:5173
```

The frontend defaults to this API URL:

```text
http://localhost:8000
```

Override it with:

```bash
VITE_HAXJOBS_API_URL=http://localhost:8000 npm run dev
```

## Testing and verification

Backend tests:

```bash
uv run pytest -q
```

Frontend tests/build:

```bash
cd frontend
npm run test:unit -- --run
npm run build
```

Full local verification:

```bash
uv run pytest -q
cd frontend && npm run test:unit -- --run && npm run build
```

## Versioning and releases

HaxJobs uses version lines like `0.1.x`, `0.2.x`, `0.3.x`.

Policy:

- Each version slice gets its own commit.
- Subversions like `v0.1.1` are tagged, but do not get GitHub releases.
- Major line milestones like `v0.1.0`, `v0.2.0`, `v0.3.0` get GitHub releases.
- Major release notes should be more explanatory than normal commits.
- `CHANGELOG.md` should explain what changed, why it matters, and what the next line unlocks.

A GitHub Actions workflow in `.github/workflows/major-release.yml` creates releases only for tags matching:

```text
vX.Y.0
```

Example:

```bash
git tag -a v0.2.0 -m "v0.2.0 — Hermes task queue foundation"
git push origin main --tags
```

## Product direction

HaxJobs is not trying to automate risky job applications first.

The product path is:

1. Save and track jobs.
2. Store truthful reusable profile facts and answers.
3. Let Hermes analyze jobs and generate application packs.
4. Review generated documents/messages inside HaxJobs.
5. Add browser capture surfaces.
6. Only later add assisted apply flows with explicit human approval gates.

No final application submission or outreach send should happen without user approval.
