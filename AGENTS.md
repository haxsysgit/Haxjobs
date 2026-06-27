# HaxJobs — Agent Guide

HaxJobs is Arinze's agent-maintained job discovery and application pipeline. Agents working in this repo MUST respect these boundaries.

## Repo layout

| Environment | Path | Role |
|---|---|---|
| Jade (local dev) | `/home/hax/haxjobs` | Coding, testing, planning |
| Archilles (live VPS) | `/home/hermes/haxjobs` | Cron, API, dashboard, Telegram |
| GitHub | `haxsysgit/Haxjobs` | Source of truth |

Workflow: develop on Jade → push to GitHub → Archilles runs `haxjobs-update` to pull.

## Verification commands

Run these from the repo root before claiming changes are safe:

```bash
python3 -m pytest -q
python3 -m py_compile $(find . -path './dashboard/node_modules' -prune -o -path './.git' -prune -o -path './.venv' -prune -o -name '*.py' -print)
bash -n cron/run_pipeline.sh scripts/haxjobs-update dashctl.sh build-dash.sh dev-watch.sh pack_builder.sh
cd dashboard && npx tsc -b --noEmit && npm run lint -- --quiet && npm run build
```

## Read/write boundaries

**Never commit:**
- `intake/`, `packs/`, `state/`, `reports/`, `outreach/` (runtime dirs)
- SQLite databases (`.db`)
- `.env` files
- LinkedIn cookies or browser profiles
- Generated CV PDFs/HTML (under `cv_variants/*/`)
- `node_modules/`, `dist/`, Vite build artifacts

**Read but don't modify:**
- Live runtime data on Archilles (`/home/hermes/haxjobs/state/pipeline.db`)
- Archilles crontab (use `crontab -l` read-only)

## Safety rules

- **Do not** submit applications, connect on LinkedIn, or send outreach messages. These require Arinze's explicit approval.
- **Do not** send Telegram messages except from Archilles via the approved Telegram bot path.
- **Do not** generate per-job CVs. Use the reusable CV variant system (5-7 variants, role-family routing).
- **Do not** auto-run pack generation from cron. Packs are gated behind manual generation + approval.
- **Do not** bind the API server to `0.0.0.0` without explicit configuration (`HAXJOBS_API_HOST`).
- **Do not** read or print `.env` values, tokens, or passwords.
- **Do not** set the `HAXJOBS_API_TOKEN` env var unless you intend to enable token auth.

## Product rules

- **SQLite** (`state/pipeline.db`) is the target source of truth for jobs, evaluations, packs, and outreach.
- **Intake JSON** files are raw import artifacts. Do not add new write paths to them.
- **Reusable CV variants** live in `cv_variants/`. Jobs are routed to them via `role_family`.
- **Pack generation** is manual/gated: `POST /api/jobs/generate-pack` or CLI, then review via `POST /api/jobs/review-pack`.
- **Outreach drafts** are template-generated and require approval before any send action.

## Coding style

- Readable Python and TypeScript. No cryptic one-liners.
- Tests use temporary SQLite DB monkeypatches. See `tests/test_manual_pack_generation.py` for the pattern.
- Match existing naming: `list_jobs()`, `insert_job()`, camelCase for API fields.
- Python stdlib HTTP server (no FastAPI). React + TypeScript + Vite dashboard.
