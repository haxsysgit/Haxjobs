# HaxJobs Architecture

HaxJobs is a self-hosted job-search web app. The current app is a Python package under `src/haxjobs`, a FastAPI backend mounted at `/api`, a React/Vite frontend under `frontend/`, and SQLite state under `state/`.

## Runtime shape

```text
React frontend (frontend/)
  ↓ /api
FastAPI app (src/haxjobs/app.py)
  ↓
Feature route modules (src/haxjobs/features/*/routes.py)
  ↓
Services, native agent harness, discovery scrapers, pack builder
  ↓
SQLite (state/haxjobs.db) and runtime profile (state/profile.json)
```

The backend also serves the built SPA from `frontend/dist` when running the local app on `localhost:8241`.

## Main components

- `src/haxjobs/app.py` creates the FastAPI app, mounts `/api/*` feature routes, serves static frontend assets, and provides the SPA catch-all route.
- `src/haxjobs/server/main.py` runs uvicorn for local development and production-like starts.
- `src/haxjobs/config.py` parses repo product config from `haxjobs.toml`; provider credentials are handled separately by setup code under `~/.haxjobs/haxjobs.toml`.
- `src/haxjobs/db/` owns SQLite schema and CRUD helpers.
- `src/haxjobs/discovery/` owns ATS scrapers, normalization, and discovery filters.
- `src/haxjobs/evaluate/` builds evaluation prompts, calls the native agent, validates JSON, and triggers auto-pack generation for configured levels.
- `src/haxjobs/agent/` is the small native agent harness with scoped tools, prompt tiers, and provider-backed LLM calls.
- `src/haxjobs/packs_builder/` creates markdown-first application packs that reference reusable CV variants.
- `frontend/src/` contains the React pages, layout, and shadcn-style UI components.
- `cron/` contains scheduled pipeline/report entrypoints that run package modules via `PYTHONPATH=src:.`.

## Data flow

```text
ONBOARD → DISCOVER → CLASSIFY → EVALUATE → DECIDE → LEARN
```

1. Onboarding writes the runtime profile to `state/profile.json` after CV extraction and user confirmation.
2. Discovery scrapers normalize jobs into `discovered_jobs`.
3. Discovery hooks accept, reject, dedupe, and promote accepted jobs into `jobs`.
4. Classification fields such as `role_family` and `recommended_cv_variant` are added through the normal job insertion path.
5. Evaluation uses the native `Agent` plus `extract_json()` validation and writes `evaluations`.
6. L1/L2 jobs can generate markdown packs using reusable CV variants and templates.
7. User decisions are recorded in `decisions` and feed later learning work.

## Profile and config

- Runtime profile: `state/profile.json` via `haxjobs.config.PROFILE_PATH`.
- Product config: repo-root `haxjobs.toml`.
- Provider credentials: `~/.haxjobs/haxjobs.toml`, written by setup, not used as product config.
- SQLite DB: `state/haxjobs.db` by default.

## Verification

From repo root:

```bash
PYTHONPATH=src:. python3 -m py_compile $(find src tests cron -name '*.py')
PYTHONPATH=src:. python3 -m pytest -q tests/
bash -n cron/run_pipeline.sh
cd frontend && npx tsc --noEmit && npm run build
```
