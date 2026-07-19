# HaxJobs Agent Guide

HaxJobs is a career agent focused on getting the user interviews and making them more employable. It is not a generic coding agent, a CV keyword spinner, or an automatic application bot.

Read these before changing direction:

1. `docs/PRODUCT.md` — what HaxJobs is and what Hax does
2. `docs/HAXJOBS.md` — current tech, concerns, and improvement areas
3. `docs/ARCHITECTURE.md` — what the code does today
4. `docs/DATA_MODEL.md` — current storage and planned career memory
5. `docs/ROADMAP.md` — build order

## Direction

HaxJobs is CLI first.

The CLI, web app, and future cloud worker must call the same Python product actions. Do not duplicate business logic in route handlers, CLI commands, cron scripts, or agent tools.

```text
CLI             Web API             Cloud worker
 \                 |                    /
  \                |                   /
       shared product actions
                 |
       SQLite + profile + files
```

The web app remains useful, but it is an interface over the product. It is not the product boundary.

The future cloud worker should run discovery and monitoring continuously. That runtime does not exist yet. Do not document it as built.

## Current reality

Implemented product actions in `src/haxjobs/product_tools.py`:

- `discover_jobs`
- `evaluate_fit`
- `generate_pack`
- `record_decision`

Registered support and profile tools:

- `web_search`
- `fetch_page`
- `db_query`, available only when an admin caller explicitly selects it
- `profile_read`
- `profile_write`
- `profile_schema`
- `profile_gaps`

The installed CLI currently exposes only:

- `haxjobs start`
- `haxjobs agent ask`
- `haxjobs dev reset|status|restart`

First-class CLI commands for discovery, evaluation, decisions, packs, and profile work are still missing.

## Architecture rules

- Business logic belongs in shared Python actions, not the agent loop.
- The agent loop chooses tools, dispatches calls, and returns results.
- FastAPI routes should call the same product actions as agent tools.
- Evaluation, decision, and pack routes already do this. Discovery still has a separate service path that must be removed.
- New interfaces must reuse shared actions directly.
- SQLite is the current source of truth for jobs, evaluations, decisions, packs, outreach records, and activity.
- `state/profile.json` is the current profile store. The planned career graph is not built.
- Product config lives in repo-root `haxjobs.toml`.
- Provider credentials live in `~/.haxjobs/haxjobs.toml`.
- Runtime paths come from `src/haxjobs/config.py`. Do not hardcode checkout paths.

## Product rules

- Everything starts from the user's profile and evidence.
- CV variants are role-specific and configured per user. Never hardcode a count.
- Do not generate a fresh CV for every job.
- Do not invent skills, metrics, experience, contacts, or company facts.
- Bad-fit jobs should eventually produce a path toward employability, not just a low score. That loop is not built yet.
- Keep discovery filters deterministic where practical. LLM work should enrich the deterministic base.
- Apply, maybe, save, skip, and reject decisions must be recorded.

## Safety

Never:

- submit an application without explicit approval
- send outreach or connect on LinkedIn without explicit approval
- expose provider credentials or private runtime files
- bind beyond loopback by default
- give normal product flows raw SQL access
- allow fetched web content to override system rules
- commit `state/`, `packs/`, `reports/`, `outreach/`, `intake/`, databases, credentials, generated CVs, or frontend build output

## Main paths

```text
src/haxjobs/agent/          agent loop, registry, prompts, tool adapters
src/haxjobs/product_tools.py shared product actions
src/haxjobs/discovery/      ATS discovery and promotion
src/haxjobs/evaluate/       fit prompt, parsing, validation
src/haxjobs/packs_builder/  application pack generation
src/haxjobs/db/             SQLite schema and queries
src/haxjobs/features/       FastAPI routes and services
src/haxjobs/profile/        profile schema and helpers
src/haxjobs/cli.py          installed CLI
frontend/                   current React interface
cron/                       current host-cron pipeline
```

## Coding rules

- Read the real caller chain before changing shared behavior.
- Reuse existing functions before adding another layer.
- Delete stale abstractions and placeholders instead of keeping compatibility wrappers.
- Use plain Python and standard library features where they hold.
- Keep code obvious. No cryptic one-liners.
- Add the smallest test that proves non-trivial behavior.
- `ponytail:` comments mark deliberate shortcuts with a real ceiling and upgrade trigger.

## Verification

Run from the repo root:

```bash
PYTHONPATH=src:. uv run python3 -m pytest -q tests/
PYTHONPATH=src:. uv run python3 -m py_compile $(find src tests cron -name '*.py')
bash -n cron/run_pipeline.sh
cd frontend
npx tsc --noEmit
npm run lint -- --quiet
npm run build
```

Use pytest for backend behavior and `agent_browser` for browser behavior. Do not mutate the shared dev server with ad hoc API calls.
