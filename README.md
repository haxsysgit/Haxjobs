# HaxJobs

HaxJobs is the UI, state, and workflow layer for a Hermes-powered job application pipeline.

Hermes does the heavy lifting: analysis, pack generation, contact discovery, outreach drafting, and approval-gated apply assistance. HaxJobs keeps the durable product surface: dashboard, profile questions, task queue, packs, approvals, and job-search state.

## Current build slice

We are starting the 0.1.x foundation line.

Implemented here:

- 0.1.0 app skeleton
  - FastAPI backend
  - Vue 3 + Vite frontend created with `create-vue`
  - `/health` endpoint
  - frontend health check against the backend
- 0.1.1 database foundation
  - SQLAlchemy engine/session setup
  - SQLite local default
  - Alembic migration pipeline
  - initial migration baseline

## Requirements

- Python 3.12+
- uv
- Node 20.19+ or 22.12+
- npm

## Backend setup

```bash
uv sync
uv run pytest
uv run alembic upgrade head
uv run uvicorn haxjobs_api.main:app --app-dir backend --reload
```

Backend health endpoint:

```text
GET http://localhost:8000/health
```

Expected response:

```json
{"status":"ok","service":"haxjobs-api"}
```

## Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Frontend defaults to this API URL:

```text
http://localhost:8000
```

Override it with:

```bash
VITE_HAXJOBS_API_URL=http://localhost:8000 npm run dev
```

## Tests

Backend:

```bash
uv run pytest
```

Frontend:

```bash
cd frontend
npm run test:unit -- --run
npm run build
```

## Local data

Local database and generated documents live under:

```text
data/
  haxjobs.db
  documents/
```

The data directory is ignored except for `.gitkeep` placeholders.
