# HaxJobs Technical Overview

The technical reality of HaxJobs today. For product direction, read `docs/PRODUCT.md`.

## Architecture

The legacy agent, web app, product tools, database layer, scrapers, and cron pipeline were deleted at the greenfield wipe. What remains is the new four-layer runtime:

```
interfaces (CLI, future web app, future worker)
  → employment layer (Hax identity, career context, fixtures)
  → agent core (messages, tools, turn, session, durable boundaries)
  → model boundary (provider adapter, fake)
```

The model boundary knows nothing about careers. The agent core knows nothing about employment. The employment layer contains all Hax and job-search logic. Interfaces call the same layer without duplicating business logic.

### Built

- `src/haxjobs/model/` — `ModelClient` protocol, `OpenAIModelClient` (max_retries=0), `FakeModelClient`, normalized `ModelRequest`/`ModelResponse`/`ModelFailure` types
- `src/haxjobs/agent_core/` — domain-free messages, tool registry with execution context, bounded turn runtime with durable tool boundaries, session persistence with dangling call detection, content-free measurement
- `src/haxjobs/employment/` — Pydantic models (Person, CareerTrack, Skill, Evidence, Job, JobAssessment), career graph store, migration, job source fetcher, employment tools (get_job, inspect_job_source, record_job_assessment), career context assembly with evidence content
- `src/haxjobs/interfaces/` — `haxjobs chat` (interactive terminal), `haxjobs profile` (CLI management)
- `src/haxjobs/config.py` — paths from `haxjobs.toml`
- `src/haxjobs/cv_variants/` — user CV variant templates, registry, renderer (data, not code to rebuild)

248 tests pass (all tests, including PTY terminal tests with isolated temp career DB). Stage 0/1 experiment runtime deleted after conversational runtime trajectories passed.

### What was deleted

- `src/haxjobs/agent/` — legacy agent loop, registry, tools, prompts
- `src/haxjobs/features/` — FastAPI route groups for decisions, discovery, evaluation, jobs, onboarding, packs, profile, setup
- `src/haxjobs/app.py` — FastAPI app
- `src/haxjobs/server/` — uvicorn runner
- `src/haxjobs/product_tools.py` — discover_jobs, evaluate_fit, generate_pack, record_decision
- `src/haxjobs/db/` — SQLite layer (schema, queries, models)
- `src/haxjobs/discovery/` — Greenhouse, Ashby, Lever scrapers
- `src/haxjobs/evaluate/` — evaluation pipeline
- `src/haxjobs/evaluation/` — role family classification
- `src/haxjobs/packs_builder/` — pack generation
- `src/haxjobs/pipeline_db.py` — cron pipeline entrypoints
- `src/haxjobs/generate_ready_packs.py`
- `cron/` — run_pipeline.sh, generate_cycle_report.py

All of these rebuild from scratch on the greenfield runtime, one stage at a time.

## What uses what

### Provider configuration

- `~/.haxjobs/haxjobs.toml` stores DeepSeek credentials (api_key, base_url, model). Mode 0600.
- `OpenAIModelClient` reads from this file. Raises `ValueError` when required keys are missing.
- DeepSeek v4 flash is the current configured model.

### Product config

- `haxjobs.toml` (repo root) — product config: paths, runtime settings.
- `src/haxjobs/config.py` — loads it. Other modules import from here, not from the file directly.

## Current limitations

### Harness gaps

1. **No context compaction.** No token tracking, compaction triggers, or context-window awareness.
2. **No cross-process session locking.** Concurrent same-session processes are explicitly deferred.
3. **No source observation history.** Current snapshot only; assessment hash preserves which snapshot was used.
4. **No user decisions.** Append-only assessments exist. User decisions are Plan 005.

### Deferred features

| Feature | Activation trigger |
|---|---|
| Compaction | When multi-turn exceeds 75% of context window |
| Token budget tracking | When costs become measurable |
| RunContext / resume | When workflows need mid-run checkpoints |
| Parallel dispatch | When 10+ evaluations bottleneck |
| JSON mode | When DeepSeek reliably supports it |
| Provider fallback cascade | When DeepSeek has reliability problems |

### Docs

- `docs/PRODUCT.md` — product direction
- `docs/HAXJOBS.md` — this file
- `docs/harness-primitives/` — agent harness teaching vault
- `discussion/` — architecture decisions and research

## Verification

```bash
PYTHONPATH=src:. uv run python3 -m pytest -q tests/
PYTHONPATH=src:. uv run python3 -m py_compile $(find src tests -name '*.py')
PYTHONPATH=src:. uv run -- haxjobs chat --help
```
