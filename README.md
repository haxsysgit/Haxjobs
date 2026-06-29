# HaxJobs

HaxJobs is Arinze's agent-native job-search workbench. It discovers jobs, evaluates fit, fills application packs from reusable templates, and produces cycle reports — all driven by a config file and a cron tick.

The goal is to make it work fully for Arinze first, then strip the personal bits and ship it as an installable pipeline that any agent (Claude, Codex, Gemini, Cursor, Cline, OpenClaw, Hermes) can run.

## Pipeline

```
DISCOVERY → CLASSIFICATION → EVALUATION → PACK GENERATION → REPORT
```

1. **Discovery** — scrapers find jobs, dedup and filter against `haxjobs.toml`, store raw jobs.
2. **Classification** — profile-driven from config, no hardcoded taxonomy.
3. **Evaluation** — pluggable agents score fit, assign levels (L1–L4).
4. **Pack Generation** — pre-built role templates get filled with job-specific slots. L1/L2 auto-fill. L3/L4 go to the report for manual review.
5. **Report** — markdown digest of every evaluated job with links, scores, pack paths. Delivered via configured channels.

## Config

`haxjobs.toml` is the canonical config. `haxjobs_config.py` is a thin parser. Env vars override. Nothing is hardcoded.

## Development

```bash
./dev-app.sh start                     # backend + frontend
PYTHONPATH=. python3 -m pytest -q tests/   # tests (PYTHONPATH required)
```

## What's not committed

`intake/`, `packs/`, `state/`, `reports/`, `outreach/`, SQLite databases, `.env` files, LinkedIn cookies, `node_modules/`, Vite build artifacts.

## Checks

Agents should read `AGENTS.md` before changing code.

From repo root:

```bash
PYTHONPATH=. python3 -m pytest -q tests/
PYTHONPATH=. python3 -m py_compile $(find . -path './dashboard/node_modules' -prune -o -path './.git' -prune -o -path './.venv' -prune -o -name '*.py' -print)
bash -n cron/run_pipeline.sh
cd dashboard && npx tsc -b --noEmit && npm run lint -- --quiet && npm run build
```
