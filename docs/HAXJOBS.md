# HaxJobs Technical Overview

The technical reality of HaxJobs today. For product direction, read `docs/PRODUCT.md`.

## Architecture

The legacy agent, web app, product tools, database layer, scrapers, and cron pipeline were deleted at the greenfield wipe. What remains is the new four-layer runtime:

```
interfaces (CLI, future web app, future worker)
  → employment layer (Hax identity, career context, fixtures)
  → agent core (model loop, dispatch, events, lifecycle)
  → model boundary (provider adapter, fake)
```

The model boundary knows nothing about careers. The agent core knows nothing about employment. The employment layer contains all Hax and job-search logic. Interfaces call the same layer without duplicating business logic.

### Built

- `src/haxjobs/model/` — `ModelClient` protocol, `OpenAIModelClient` (max_retries=0), `FakeModelClient`, normalized `ModelRequest`/`ModelResponse`/`ModelFailure` types
- `src/haxjobs/agent_core/` — domain-free `RunRequest`/`RunResult`, lifecycle events (`RunEvent`, `RunObserver`), `ArtifactWriter` (0700 dirs, 0600 files), stage0 runtime (exactly one model call, no tools)
- `src/haxjobs/employment/` — Pydantic fixtures (`CareerFixture`, `JobFixture`, `EvidenceItem`), Hax identity and truth rules, job-review context assembler
- `src/haxjobs/interfaces/` — thin `experiment review-job` CLI with `--fake` and `--live` modes
- `src/haxjobs/config.py` — paths from `haxjobs.toml`
- `src/haxjobs/cv_variants/` — user CV variant templates, registry, renderer (data, not code to rebuild)

27 tests pass. Live experiment ran successfully against deepseek-v4-flash. Three independent Flash reviewers found zero issues.

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

1. **No sessions.** No concept of a durable conversation. Every model call is stateless.
2. **No context management.** No token tracking, compaction, or context-window awareness.
3. **No tool loop.** Stage 0 is one call with no tools. inspect_job_source is Plan 002.
4. **No durable state.** No career memory, evaluation store, decision log, or commitment records.
5. **No CLI parity.** Only one command exists: `experiment review-job`.

### Deferred features

| Feature | Activation trigger |
|---|---|
| Compaction | When multi-turn exceeds 75% of context window |
| Token budget tracking | When costs become measurable |
| RunContext / resume | When workflows need mid-run checkpoints |
| Parallel dispatch | When 10+ evaluations bottleneck |
| JSON mode | When DeepSeek reliably supports it |
| Conversation loop | When interactive chat is added |
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
PYTHONPATH=src:. uv run haxjobs experiment review-job --job 49 --fake --career-fixture tests/fixtures/job_review/career.json
```
