# HaxJobs — Pi Handoff

Yo Pi. HaxJobs is Arinze's self-hosted job search platform. It builds a structured profile from a CV upload, discovers jobs, evaluates fit, generates application packs, learns from user decisions, and helps with outreach.

**Read `docs/PRODUCT_ARCHITECTURE.md` first** — it's the canonical vision. This handoff covers repo conventions and current state.

## What HaxJobs is

A self-hosted web app (Python + React + SQLite) that runs at `localhost:8241`. Six phases:

```
ONBOARD → DISCOVER → CLASSIFY → EVALUATE → DECIDE → LEARN
```

Plus outreach (hiring manager discovery, message generation, status tracking).

## Current state

### Built and working
- **Profile JSON** (`profile/arinze_profile.local.json`) — backbone of everything, hand-maintained for now. Will be built by onboarding wizard (wave 6B).
- **Discovery** — Greenhouse, Ashby, Lever scrapers with profile-aware pre-filtering, hooks (blacklist, location, non-tech), orchestrator
- **Classification** — config-driven from `haxjobs.toml` `[[roles]]`, 7 role families
- **Evaluation** — prompt builder, JSON parser, validator, 3 working adapters (Codex, Hermes, Pi), config-driven chain with fallback
- **CV review** — per-job CV review with JD keyword injection and role-specific framing
- **Auto-pack** — L1/L2 jobs get packs generated from templates
- **Cycle reports** — `reports/<cycle>.md` markdown digest
- **CLI** — `pipeline_db.py` with 18 commands including `run-full` (end-to-end)
- **Dashboard** — React + TypeScript web UI shell (needs decision loop UI)
- **API server** — stdlib HTTP server with REST endpoints

### Not yet built (waves 6B-8)
- **Onboarding wizard** — CV upload → LLM extraction → guided questions → profile.json
- **Decision loop** — user marks apply/skip/reject from dashboard, `decisions` table wired up
- **Direct LLM API evaluation** — replace agent subprocess adapters for headless cron
- **Learning engine** — processes decisions, evolves profile preferences
- **Outreach engine** — hiring manager discovery, message generation, status tracking
- **DB lifecycle** — cycle tracking, job archiving, between-cycle cleanup
- **Product packaging** — `pip install haxjobs`, one-command start
- **Web search discovery** — open web job search beyond ATS scrapers

## Config

`haxjobs.toml` is canonical. `haxjobs_config.py` is the thin parser. Env vars override TOML values.

Sections: `[paths]`, `[user]`, `[job_search]`, `[[roles]]`, `[evaluation]`, `[delivery]`, `[cron]`, `[email]`, `[telegram]`.

## DB layout

SQLite (`state/haxjobs.db`). Key tables:

- `discovered_jobs` — raw scraped, pre-filtering
- `jobs` — promoted, classified, evaluated (status: pending/evaluated/skipped)
- `evaluations` — fit results (score, level, matches, gaps, agent, cycle_id)
- `decisions` — apply/skip/reject per job (schema exists, needs UI writer)
- `outreach_drafts`, `outreach_contacts` — schema exists, needs implementation
- `whitelist` — learned patterns
- `activity_log` — pipeline events

Deprecated (will be removed): `favorites`, `saved_jobs`, `evaluation_history` — replaced by `decisions` + `cycle_id` on evaluations.

Future tables (per PRODUCT_ARCHITECTURE.md): `cycle_state`, `job_history`, `learning_patterns`.

## Repo conventions

- Python: stdlib-focused, imports from `haxjobs_config`, DB via `db/*` modules, no ORM, `ponytail:` comments mark deliberate simplifications
- Bash: `set -euo pipefail`, lowercase functions
- Tests: `pytest` with `tmp_path` + `monkeypatch` for DB isolation, shared `test_db` fixture in `conftest.py`
- Commits: casual direct commits with descriptive messages (no conventional commit prefixes)
- SQLite is source of truth — no JSON split-brain
- Config is TOML first — never hardcode paths, agent names, or preferences

## Key files

| File | Role |
|------|------|
| `haxjobs.toml` | Canonical config |
| `haxjobs_config.py` | Thin TOML parser, exports constants |
| `profile/arinze_profile.local.json` | Profile backbone |
| `AGENTS.md` | Full agent guide with rules and product conventions |
| `docs/PRODUCT_ARCHITECTURE.md` | Canonical product vision |
| `docs/ARCHITECTURE.md` | Technical architecture |
| `docs/DATA_MODEL.md` | Database schema |
| `pipeline_db.py` | CLI (18 commands) |
| `api_server.py` | HTTP API server |
| `evaluate/common.py` | Prompt building, JSON parsing, validation |
| `evaluate/chain.py` | Config-driven agent chain |
| `evaluate/run.py` | Evaluation flow + auto-pack |
| `db/schema.py` | SQLite schema + migrations |
| `discovery/scrapers/orchestrator.py` | Scraper runner |
| `cron/run_pipeline.sh` | Scheduled pipeline entry |

## Verification commands

```bash
PYTHONPATH=. python3 -m pytest -q tests/
PYTHONPATH=. python3 -m py_compile $(find . -path './dashboard/node_modules' -prune -o -path './.git' -prune -o -path './.venv' -prune -o -name '*.py' -print)
bash -n cron/run_pipeline.sh
cd dashboard && npx tsc -b --noEmit && npm run lint -- --quiet && npm run build
```

## Read/write boundaries

**Never commit:** `intake/`, `packs/`, `state/`, `reports/`, `outreach/`, `.db` files, `.env`, LinkedIn cookies, CV PDFs/HTML, `node_modules/`, `dist/`

**Read but don't modify:** Archilles live DB, Archilles crontab

## Safety rules

- Never submit applications, connect on LinkedIn, or send outreach without Arinze's approval
- Never send Telegram except through configured delivery channel
- Never generate per-job CVs — use 7 reusable variants
- L1/L2 auto-pack, L3/L4 manual review only
- Never bind API to `0.0.0.0` without explicit config
- Never read or print `.env` values, tokens, or passwords
- Never set `HAXJOBS_API_TOKEN` unless enabling token auth

## What to work on next

See `plans/README.md` — currently executing wave 6 (docs alignment). Next: wave 6B (product foundation — onboarding, decisions, direct LLM API, profile evolution).
