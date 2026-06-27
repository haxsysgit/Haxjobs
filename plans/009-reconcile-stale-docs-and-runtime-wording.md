# Plan 009: Reconcile stale docs and runtime wording

> **Executor instructions**: Follow this plan step by step. Run every verification command and confirm expected results. Stop on any STOP condition.
>
> **Drift check (run first)**: `git diff --stat b725a33..HEAD -- README.md docs cron/run_pipeline.sh dashboard/package.json api_server.py`

## Status

- **Priority**: P3
- **Effort**: S
- **Risk**: LOW
- **Depends on**: plans/001-restore-verification-baseline.md
- **Category**: docs
- **Planned at**: commit `b725a33`, 2026-06-27

## Why this matters

Some docs describe older stack and runtime assumptions. They still say FastAPI/Vue even though the active app is a stdlib Python HTTP API plus React/Vite, and `cron/run_pipeline.sh` says every 3 hours while repo docs say every 30 minutes. Stale docs mislead agents and create cleanup churn.

## Current state

Relevant files:
- `docs/ARCHITECTURE.md`
- `docs/ROADMAP.md`
- `docs/REPO_MAP.md` if present/live in checkout
- `cron/run_pipeline.sh`
- `dashboard/package.json`
- `api_server.py`

Current excerpts:
- `docs/ARCHITECTURE.md:61-68`: recommended MVP stack lists Backend Python/FastAPI and Frontend Vue 3/Vite.
- `docs/ROADMAP.md:91-97`: repeats Backend Python + FastAPI and Frontend Vue 3 + Vite.
- `dashboard/package.json:12-15`: active dependencies are `react`, `react-dom`, `react-router-dom`.
- `api_server.py:10`: imports `HTTPServer, BaseHTTPRequestHandler`, not FastAPI.
- `cron/run_pipeline.sh:4`: says run by system crontab every 3 hours.
- `cron/run_pipeline.sh:53-54`: repeats system crontab fires every 3h.
- Repo docs/skill say current Archilles cadence is every 30 minutes, but the executor should verify live crontab before claiming it as fact.

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| Search stale stack | `grep -R "Vue 3\|FastAPI\|every 3 hours\|every 3h" -n README.md docs cron/run_pipeline.sh` | No stale unqualified claims remain |
| Diff check | `git diff --check -- README.md docs cron/run_pipeline.sh` | exit 0 |
| Shell syntax | `bash -n cron/run_pipeline.sh` | exit 0 |

## Scope

In scope:
- Docs and comments only: `docs/*.md`, `README.md`, `cron/run_pipeline.sh` comments.
- If live cadence can be verified without side effects, update docs accordingly.

Out of scope:
- Changing actual cron schedule.
- Changing runtime behavior.
- Rewriting the roadmap wholesale.

## Git workflow

- Branch suggestion: `advisor/009-reconcile-docs-runtime`

## Steps

### Step 1: Correct active stack docs

Update docs that describe the active/current stack:
- Backend: Python stdlib HTTP server in `api_server.py` today; FastAPI may be future/older plan only if explicitly marked as historical/future.
- Frontend: React + TypeScript + Vite in `dashboard/` today; Vue references should be marked historical/rejected or removed from active recommendations.

Do not erase useful roadmap history. Just prevent readers from thinking Vue/FastAPI are the current active stack.

Verify: `grep -R "Vue 3\|FastAPI" -n README.md docs` → any remaining hits are explicitly historical/future, not current active stack.

### Step 2: Reconcile pipeline cadence wording

First, inspect repo evidence. If you have safe SSH access and operator context permits, verify live Archilles crontab with a read-only command such as `ssh archilles 'crontab -l | grep run_pipeline || true'`. If SSH is unavailable, do not claim live truth; write “repo docs indicate 30 minutes, verify live crontab before operational changes.”

Update comments/docs so `cron/run_pipeline.sh` does not say every 3 hours if that is stale. If live verification confirms `*/30`, say every 30 minutes. If not verified, say “scheduled by system crontab; current repo docs expect every 30 minutes.”

Verify: search for `every 3 hours` and `every 3h` in docs and cron comments.

### Step 3: Keep command checks current

Ensure README Checks still match Plan 001 baseline: pytest, Python compile, shell syntax, dashboard build. Do not add commands that require secrets or live Archilles.

Verify diff check and shell syntax.

## Test plan

Docs/comment-only. Run grep and diff checks. Run `bash -n cron/run_pipeline.sh` if comments changed in shell file.

## Done criteria

- [ ] Active stack docs say React/Vite dashboard and Python stdlib API, or clearly mark FastAPI/Vue as historical/future.
- [ ] Pipeline cadence wording no longer says every 3 hours unless live crontab actually says that.
- [ ] README Checks remain accurate.
- [ ] `git diff --check -- README.md docs cron/run_pipeline.sh` exits 0.
- [ ] `bash -n cron/run_pipeline.sh` exits 0.
- [ ] No runtime/source behavior changes are made.
- [ ] `plans/README.md` row 009 updated when done.

## STOP conditions

Stop and report if:
- Live Archilles crontab conflicts with repo docs and the intended cadence is unclear.
- Docs intentionally preserve FastAPI/Vue as a future migration target and Arinze needs to decide whether to keep that direction.

## Maintenance notes

Docs should distinguish “current active stack” from “future possible migration.” Agents should not be left guessing.
