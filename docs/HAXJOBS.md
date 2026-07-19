# HaxJobs Technical Overview

This file describes the technical reality of HaxJobs today: what runs, what does not, what is stale, and what needs attention. For product direction, read `docs/PRODUCT.md`.

## Architecture

HaxJobs mirrors Pi's four-layer separation inside one Python package:

```
interfaces (CLI, FastAPI, future worker)
  → employment layer (Hax identity, career context, evidence, tools)
  → agent core (model loop, dispatch, events, lifecycle)
  → model boundary (provider adapter, fake, types)
```

The model boundary knows nothing about careers. The agent core knows nothing about employment. The employment layer contains all Hax and job-search logic. Interfaces call the same layer without duplicating business logic.

### Greenfield runtime (built)

Stage 0 of the new runtime is implemented:

- `src/haxjobs/model/` — `ModelClient` protocol, `OpenAIModelClient` (max_retries=0), `FakeModelClient`, normalized `ModelRequest`/`ModelResponse`/`ModelFailure` types
- `src/haxjobs/agent_core/` — domain-free `RunRequest`/`RunResult`, lifecycle events (`RunEvent`, `RunObserver`), `ArtifactWriter` (0700 dirs, 0600 files), stage0 runtime (exactly one model call)
- `src/haxjobs/employment/` — Pydantic fixtures (`CareerFixture`, `JobFixture`, `EvidenceItem`), Hax identity and truth rules, job-review context assembler
- `src/haxjobs/interfaces/` — thin `experiment review-job` CLI with `--fake` and `--live` modes

27 tests pass. Live experiment ran successfully against deepseek-v4-flash. Three independent Flash reviewers found zero issues.

### Legacy agent (still present, superseded)

`src/haxjobs/agent/` contains the pre-reset agent loop:

- `Agent.run()` and `Agent.run_with_tools(max_turns=5)` — thin OpenAI-compatible wrapper
- `registry.py` — tool registration, schema filtering, and dispatch
- `tools.py` — imports tool modules so they register globally
- `tool_modes.py` — workflow-specific allowlists
- `prompt.py` — stable/flow/volatile three-tier prompt assembly
- `identity.py` — loads `~/.haxjobs` identity

11 tools are registered: discover_jobs, evaluate_fit, generate_pack, record_decision, profile_read, profile_write, profile_schema, profile_gaps, web_search, fetch_page, db_query.

The legacy agent was not deleted during the greenfield build. The greenfield runtime does not import it.

### Product actions (legacy, still in use)

`src/haxjobs/product_tools.py` implements four shared actions:

- `discover_jobs` — runs Greenhouse, Ashby, and Lever scrapers
- `evaluate_fit` — calls the legacy agent with an evaluation prompt, parses JSON
- `generate_pack` — assembles an application pack from CV variants and evaluation
- `record_decision` — writes apply/maybe/save/skip/reject to the decisions table

These are shared across FastAPI services and agent tools. Discovery still has a separate service path in `src/haxjobs/features/discovery/service.py` that does not call `product_tools.py` — this duplication should be removed.

### Web app

- `src/haxjobs/app.py` — FastAPI composition with CORS and a catch-all `/{full_path:path}` route for SPA client-side routing
- `src/haxjobs/features/` — route modules per domain with `routes.py`/`schemas.py`/`service.py` pattern
- `src/haxjobs/server/main.py` — uvicorn wrapper on port 8241
- `frontend/` — React 19, TypeScript, Vite, Tailwind CSS 4, react-router-dom v7

The frontend has Dashboard, Workspace, Recon, Jobs, Packs, Config, and You pages. The Opus 4.8 UI integration replaced most pre-existing components. Some pages still use hardcoded fixture data instead of real API calls.

### Discovery pipeline

`src/haxjobs/discovery/` has scrapers for Greenhouse, Ashby, and Lever. Discovery runs through an in-process daemon thread with a module-global lock when triggered from the UI, or through the host-cron pipeline at `cron/run_pipeline.sh`. There is no durable worker, queue, service, or cloud deployment.

### Evaluation pipeline

`src/haxjobs/evaluate/` contains prompt assembly, `extract_json()` for parsing model output, and pipeline entry points. The legacy pipeline calls `Agent().run()` and parses with `extract_json()`. The old evaluator adapter stack was deleted during cleanup.

### Pack generation

`src/haxjobs/packs_builder/` generates application packs using reusable role-specific CV variants from `src/haxjobs/cv_variants/`. CV variants are role-specific and configured per user — the number depends on the user's configured roles.

### Storage

- `state/haxjobs.db` — SQLite in WAL mode. Tables: discovered_jobs, jobs, evaluations, decisions, profile_snapshots (reserved, no writer), activity_log, whitelist, outreach_contacts, outreach_drafts. Foreign keys enabled. Dev database is seeded from old scraped data (385 jobs, 374 evaluations).
- `state/profile.json` — canonical profile file. Schema defines personal, skills, work authorization, preferences, experience, projects, education, profile health, and onboarding state. Used by onboarding, evaluation, and agent tools.
- `~/.haxjobs/haxjobs.toml` — provider credentials (api_key, base_url, model). Mode 0600.
- `haxjobs.toml` (repo root) — product config: paths, runtime settings.

### Cron

`cron/run_pipeline.sh` runs discovery, evaluation, pack generation, and cycle reports using package-style invocations (`python3 -m haxjobs.pipeline_db`). Reports go to `reports/`.

## What uses what

### Shared action model

```
CLI ────────────┐
FastAPI ────────┼──→ product_tools.py → SQLite + profile + files
Agent tools ────┘
```

Evaluation, decision, and pack routes already call the shared functions. Discovery routes do not yet — they use a separate service path.

### Provider configuration

- `~/.haxjobs/haxjobs.toml` stores DeepSeek credentials (api_key, base_url, model)
- Both legacy `OpenAIModelClient` and greenfield `OpenAIModelClient` read from the same file
- The greenfield adapter raises `ValueError` when required keys are missing (no silent fallback)
- DeepSeek v4 flash is the current configured model

## Current limitations and concerns

### Architecture

1. **Two agent systems coexist.** The legacy `src/haxjobs/agent/` runs the product while the greenfield `src/haxjobs/agent_core/` runs Stage 0 experiments. They do not share code. The legacy agent should be replaced by the greenfield runtime as stages progress, not kept alongside it.

2. **No sessions, compaction, or context management.** The greenfield runtime has no session concept, no token tracking, no context-window awareness, no summarization of old turns, and no structured error recovery. The legacy agent similarly lacks these. Context management is the highest-priority harness gap.

3. **Discovery is not durable.** UI discovery runs in an in-process daemon thread with a module-global lock. Cron is a separate host path. There is no worker, queue, or cloud deployment.

4. **CLI is not at parity.** The installed CLI exposes server startup, `agent ask`, and dev commands. Discovery, evaluation, decisions, packs, and profile actions exist as product tools but have no first-class CLI commands.

5. **Profile storage is flat.** `state/profile.json` works for onboarding and evaluation but lacks independent career tracks, normalized evidence, history, and verification dates. The planned career graph is not built.

### Safety

1. **Provider setup has no local-origin guard.** Setup persists supplied credentials without checking the request origin. Server startup allows arbitrary `--host`. Binding or proxying beyond loopback could expose the provider configuration endpoint.

2. **fetch_page redirects are not fully hardened.** The fix validates the resolved URL against the original host, but fetch_page remains a vector when web content mixes with profile and DB tools in discovery prompts.

3. **State-changing routes lack CSRF protection.** GET `/onboarding/reset` (now 405) and unauthenticated POST actions are susceptible to cross-site triggering.

4. **Auto-pack paths derive from external company text.** Generated pack file paths include company names from job descriptions, which could create paths outside expected directories.

### Frontend

1. **WorkspaceClient is disconnected.** It POSTs to an absent `/api/messages` and expects a response shape the API does not return. It is not wired to the native agent or durable product APIs.

2. **Some pages use hardcoded fixture data.** The Opus integration's DashboardClient and WorkspaceClient use SEED_JOBS from `lib/fixtures.ts` instead of real API calls.

3. **No Vite proxy for `/api`.** Frontend dev server does not proxy `/api` calls to the backend, requiring either a production build or manual cors configuration.

4. **Theme has gaps.** Dark and light mode switching exists but some components render incorrectly in one mode or the other.

### Deferred harness features

These are explicitly deferred with activation triggers:

| Feature | Trigger |
|---|---|
| Compaction | When multi-turn exceeds 75% of context window |
| Token budget tracking | When costs become measurable |
| RunContext / resume | When workflows need mid-run checkpoints |
| Parallel dispatch | When 10+ evaluations bottleneck |
| JSON mode | When DeepSeek reliably supports it |
| Conversation loop | When interactive chat is added |
| Provider fallback cascade | When DeepSeek has reliability problems |
| Tool executor class | When dispatch exceeds ~50 lines |

### Docs that need attention

The following docs predate the greenfield reset and contain stale content:

- `docs/PRODUCT_ARCHITECTURE.md` — pre-reset product direction. Superseded by `docs/PRODUCT.md`.
- `docs/ARCHITECTURE.md` — describes the current codebase but predates the greenfield runtime.
- `docs/HAXJOBS_AGENT_HARNESS.md` — describes the legacy agent. Does not cover the greenfield runtime or the planned harness foundations.
- `docs/DATA_MODEL.md` — partially updated for profile storage changes. Still references old table schemas.
- `docs/ROADMAP.md` — high-level build order. Does not reflect the specific Stage 0/1 experiment sequence from `plans/`.
- `docs/implementation-reports/` — Stage 0 report only. Future stages will add more.
- `AGENTS.md` — coding rules and paths. Predates the greenfield `src/haxjobs/model/`, `agent_core/`, `employment/`, and `interfaces/` directories.
- `README.md` — partially updated. Mentions the legacy agent playground but not the greenfield experiment CLI.

### Stale files to remove or replace

- `discussion/003-company-watch-vertical-slice.md` — paused. Accepted behaviour is research input, but the domain model is not architecture. The company-watch scenario will be revisited after later stages.
- `design-culmination.md` (repo root) — old UI design notes from the 8-model competition. Parked.
- `ui-redesign-prompt.md` (repo root) — old UI redesign prompt document. Parked.
- `GPT5_HANDOFF.md` (repo root) — old GPT 5.5 handoff. Superseded by the new product direction.
- `PI_HANDOFF.md` (repo root) — stale Pi-to-HaxJobs mapping. Does not reflect the greenfield architecture or the expanded tool set.

### Verification commands

Full verification from repo root:

```bash
PYTHONPATH=src:. uv run python3 -m pytest -q tests/
PYTHONPATH=src:. uv run python3 -m py_compile $(find src tests cron -name '*.py')
bash -n cron/run_pipeline.sh
cd frontend
npx tsc --noEmit
npm run lint -- --quiet
npm run build
```

Greenfield experiment only:

```bash
PYTHONPATH=src:. uv run python3 -m pytest -q tests/test_stage0_job_review.py
PYTHONPATH=src:. uv run haxjobs experiment review-job --job 49 --fake --career-fixture tests/fixtures/job_review/career.json
```
