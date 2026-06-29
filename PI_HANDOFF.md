# HaxJobs — Pi Handoff

Yo Pi. Here is everything you need to know about HaxJobs. Current status: Plans 001-022 complete (204 tests). Next: 3-Agent Simulation Loop or deferred audit fixes.

## What HaxJobs is

HaxJobs is Arinze's agent-native job-search workbench. It finds jobs, evaluates fit, fills application packs from reusable templates, and produces cycle reports — all driven by a config file and a cron tick.

The goal: make it work fully for Arinze first, then strip the personal bits and ship it as an installable pipeline that any agent (Claude, Codex, Gemini, Cursor, Cline, OpenClaw, Hermes) can run.

## Current pipeline (5 stages)

```
DISCOVERY → CLASSIFICATION → EVALUATION → PACK GENERATION → REPORT
```

1. **Discovery** — scrapers/manual → normalize → hooks (dedup, blacklist, filter) → `discovered_jobs` table → promote to `jobs`
2. **Classification** — profile-driven from `haxjobs.toml` `[[roles]]`, assigns `role_family` + `cv_variant`
3. **Evaluation** — pluggable agent (hermes default), scores fit 0-100, assigns L1-L4
4. **Pack Generation** — L1/L2 auto-fill role templates, L3/L4 report-only
5. **Report** — cycle markdown digest, delivered via configured channels

## What's been done

### Cleanup wave 1 (plans 001-009) — DONE
Restored test baseline, locked down API, fixed LinkedIn import, enforced approval states, persisted pack dirs, batched job-list queries, characterized evaluator, added agent guide, reconciled docs.

### Wave 2 (plans 011-014) — DONE
Fixed pack file serving, fixed eval job-id bug, added pagination to /api/jobs, removed intake JSON split-brain.

### Wave 3 cleanup (plans 020-022) — DONE
Cut 10 stale tests. Swept 7 dead scripts. Aligned all docs to the current vision.

### Pipeline wave (plans 015-017) — DONE (merged to main)
- **Plan 015**: Discovery ingestion spine — `discovered_jobs` table, `discovery/` package (normalize.py + hooks.py), `db/discovered_jobs.py`, `discover-manual` / `discover-run` CLI. 8 new tests.
- **Plan 016**: Config contract — expanded `haxjobs.toml` with `[user]`, `[job_search]`, `[[roles]]` (7 families), `[evaluation]`, `[delivery]`. 10 config constants in `haxjobs_config.py`.
- **Plan 017**: Config-driven classifier + pluggable evaluator. `evaluation/role_family.py` reads from `ROLE_PROFILES` instead of hardcoded JSON. `evaluate/` package with `common.py` (prompt, parse, validate), `agents/hermes.py`, `run.py` (agent selection). `evaluate_with_hermes.py` is a backward-compat shim. 12 new role-family tests, 10 new evaluator tests.

Test count: 197.

### What's next: Plan 010 (rejected) → fresh packaging plan needed

Plans 018 and 019 are DONE. The remaining TODO (Plan 010 — package as installable engine) was written against an old repo shape (June 2026, pre 015-019) and has been rejected. A fresh packaging plan should be written against the current codebase.

Deferred audit findings (6-9, D1-D2) and the 3-Agent Simulation Loop are the natural next work.

## Repo conventions

- **Python**: stdlib-focused. Imports use `from haxjobs_config import X`. DB access via `db/*` modules through `db.schema.get_db()`. No ORM.
- **Bash**: `set -euo pipefail`, functions lowercase, log with `tee -a "$LOG_FILE"`.
- **Config**: `haxjobs.toml` is canonical, `haxjobs_config.py` parses it with `tomllib`. Env vars override.
- **Tests**: pytest with `tmp_path` + `monkeypatch` for DB isolation. Pattern:
  ```python
  def use_temp_db(monkeypatch, tmp_path):
      db_path = tmp_path / "haxjobs.db"
      monkeypatch.setattr(schema, "DB_PATH", str(db_path))
      schema.init()
  ```
- **Commit style**: casual, direct, no feat/fix/chore prefixes. Sound like a dev talking to the team. See recent commits for the vibe.
- **Ponytail**: `ponytail:` comments mark deliberate simplifications with the upgrade path.

## Key design decisions

- **SQLite is the source of truth.** Database file: `state/haxjobs.db`. No scattered JSON files. No dual-write split-brain.
- **Template-fill, not LLM-generate.** Packs fill pre-built role templates with computed slots. The LLM does evaluation, not content generation.
- **Reusable CV variants.** 7 variants (backend_python, fullstack_python_react, ai_engineer_llm, ai_automation_agents, junior_software, data_python, platform_backend). Packs reference a variant via metadata — never generate a new CV per job.
- **Human-gated actions.** No auto-submit. No auto-outreach. Arinze controls every real-world action.
- **Config-driven, not hardcoded.** Everything that can vary per user lives in `haxjobs.toml`.
- **Pluggable agents.** The evaluator uses an adapter pattern. Hermes is the default, but any agent that implements `call_agent(prompt, timeout_seconds) -> str` can be swapped in.

## haxjobs.toml contract (plan 016)

```toml
[user]
name = "Arinze Elenasulu"
location = "London, UK"
headline = "Python Backend Engineer | AI & Automation"

[job_search]
preferred_locations = ["London", "Remote UK", "Manchester", "Leeds"]
work_modes = ["remote", "hybrid", "onsite"]
employment_types = ["full_time", "contract", "graduate"]
target_levels = ["graduate", "junior", "mid"]
excluded_levels = ["senior", "lead", "principal", "staff", "manager"]
blacklisted_companies = []
blacklisted_keywords = ["sales", "marketing", "legal", "finance", "admin"]
lenient_filtering = true

[[roles]]
id = "backend_python"
label = "Python Backend Engineer"
cv_variant = "backend_python"
positive_keywords = ["python", "fastapi", "django", "flask", "backend", ...]
negative_keywords = ["ios", "android", "frontend only", ...]
priority = 1
# ... 6 more roles

[evaluation]
agent = "hermes"
timeout_seconds = 180
[evaluation.levels]
auto_pack = [1, 2]
manual_review = [3]
skip = [4]

[delivery]
channels = ["email"]
report_format = "markdown"
```

Config constants exposed by `haxjobs_config.py`: `USER_PROFILE`, `JOB_SEARCH_CONFIG`, `ROLE_PROFILES`, `EVALUATION_CONFIG`, `DELIVERY_CONFIG`, `EVALUATION_AGENT`, `DELIVERY_CHANNELS`, `AUTO_PACK_LEVELS`, `MANUAL_REVIEW_LEVELS`, `SKIP_LEVELS`.

## Verification commands

```bash
PYTHONPATH=. python3 -m pytest -q tests/                # tests (197 currently)
PYTHONPATH=. python3 -m py_compile $(find . -path './dashboard/node_modules' -prune -o -path './.git' -prune -o -path './.venv' -prune -o -name '*.py' -print)  # compile check
bash -n cron/run_pipeline.sh                            # bash syntax
cd dashboard && npx tsc -b --noEmit && npm run lint -- --quiet && npm run build  # dashboard
```

## Current file layout (key files)

```
haxjobs-private-dev/
├── haxjobs.toml              ← canonical config (paths, user, job_search, roles, evaluation, delivery)
├── haxjobs_config.py         ← thin TOML parser with env overrides
├── AGENTS.md                 ← agent guide
├── README.md                 ← project overview
├── cron/
│   └── run_pipeline.sh       ← pipeline entry point
├── pipeline_db.py            ← CLI: seed, classify-roles, discover-manual, discover-run, status, etc.
├── api_server.py             ← HTTP API server (stdlib HTTPServer)
├── evaluate_with_hermes.py   ← backward-compat shim → delegates to evaluate.run
├── generate_ready_packs.py   ← pack generation trigger
├── db/                       ← SQLite layer
│   ├── schema.py             ← table definitions + migrations
│   ├── jobs.py               ← job CRUD
│   ├── discovered_jobs.py    ← discovery ingestion (plan 015)
│   ├── evaluations.py        ← evaluation save/read
│   ├── role_classification.py  ← persists role-family from config-driven classifier
│   ├── activity.py, outreach.py, decisions.py, pack_review.py, seed.py, stats.py, favorites.py, saved.py, whitelist.py
├── discovery/                ← ingestion spine (plan 015)
│   ├── normalize.py          ← job record normalization
│   └── hooks.py              ← dedup, blacklist, filter hooks
├── evaluate/                 ← pluggable agent system (plan 017 target)
│   ├── common.py             ← JSON extraction, validation, prompt building
│   ├── agents/hermes.py      ← Hermes CLI adapter
│   └── run.py                ← agent selection + evaluation flow
├── packs_builder/
│   └── job_pack.py           ← template-fill pack generation
├── server/routes/            ← API route handlers
├── dashboard/                ← React + TypeScript + Vite
├── cv_variants/              ← 7 reusable CV variants
├── application_templates/    ← role pack templates with fillable slots
├── profile/                  ← user profile data
├── state/                    ← runtime artifacts (haxjobs.db, logs)
├── packs/                    ← generated pack directories
├── tests/                    ← test suite
├── plans/                    ← implementation plans (001-022)
└── docs/                     ← architecture and design docs
    └── diagrams/             ← draw.io pipeline diagrams
```

## Plan 018 — what's next

The plan lives at `plans/018-split-raw-and-evaluated-job-state.md`. Read it fully before starting.

In short: extend the `evaluations` table additively with `agent`, `profile_snapshot_json`, `report_markdown`, `pack_dir`, `pack_template_id`, `report_cycle_id`. Update `save_evaluation()` to accept the new optional fields. This is an additive-only migration — no destructive schema changes.

## Worktrees with pending work

Plans 015/016 changes were cherry-picked from their worktrees onto main. The worktrees (`agent-a1bc793be8b5986cd`, `agent-ad6d708d5c1c96f0b`) still exist on disk but their useful content is now on main. They can be cleaned up.

## Git hygiene

- Commit in clean logical chunks
- No feat/fix/chore prefixes
- Casual, direct tone
- Co-Authored-By: Claude <noreply@anthropic.com> on every commit
