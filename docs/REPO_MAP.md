# HaxJobs Repo Map

Last updated: 2026-07-04.

```text
haxjobs/
├── haxjobs.toml                 # Product config: paths, user, discovery, roles, evaluation, delivery, cron
├── pyproject.toml               # Python package metadata and haxjobs CLI entrypoint
├── dev                          # Local helper: restart, reset, status, build, start, test
├── AGENTS.md                    # Agent guide and safety rules
├── README.md                    # Project overview
│
├── src/haxjobs/
│   ├── app.py                   # FastAPI app, /api mount, static frontend serving, SPA fallback
│   ├── cli.py                   # haxjobs CLI, including agent and dev commands
│   ├── config.py                # TOML/env config parser; runtime paths such as STATE_DIR and PROFILE_PATH
│   ├── server/main.py           # uvicorn runner
│   ├── features/                # FastAPI feature modules: setup, onboarding, discovery, jobs, packs, profile, decisions
│   ├── db/                      # SQLite schema and CRUD helpers
│   ├── discovery/               # Normalization, hooks, Greenhouse/Ashby/Lever scrapers, orchestrator
│   ├── evaluate/                # Prompt building, JSON extraction, native-agent evaluation, CV review
│   ├── agent/                   # Native agent harness, tools, prompts, identity
│   ├── packs_builder/           # Markdown pack generation
│   ├── application_templates/   # Cover letter and pack templates
│   ├── cv_variants/             # Reusable role-specific CV variant sources and registry
│   └── profile/                 # Profile schema and review docs, not runtime user state
│
├── frontend/
│   ├── src/App.tsx              # React router setup
│   ├── src/pages/               # Dashboard, setup, onboarding, discovery, jobs, profile pages
│   ├── src/components/layout/   # Sidebar, header, route guard
│   └── src/components/ui/       # shadcn-style local UI primitives
│
├── cron/
│   ├── run_pipeline.sh          # Scheduled discovery/evaluation/report runner
│   └── generate_cycle_report.py # Markdown cycle report generator
│
├── tests/                       # pytest suite with temp SQLite fixture in tests/conftest.py
├── docs/                        # Product and technical docs
├── plans/                       # Product implementation plans
├── advisor-plans/               # Improve-skill audit findings and executor plans
│
├── state/                       # Runtime DB/profile, gitignored
├── packs/                       # Generated application packs, gitignored
├── reports/                     # Generated cycle reports, gitignored
└── outreach/                    # Generated outreach artifacts, gitignored
```

## Current source-of-truth paths

- Runtime profile: `state/profile.json` through `haxjobs.config.PROFILE_PATH`.
- Product config: repo-root `haxjobs.toml`.
- Provider credentials: `~/.haxjobs/haxjobs.toml` through setup service code.
- Frontend: `frontend/`.
- Backend API: FastAPI under `src/haxjobs/features/`, not a root server script.
- Evaluation: native `haxjobs.agent.Agent` through `src/haxjobs/evaluate/run.py`.

## Useful commands

```bash
./dev status
./dev build
./dev test
PYTHONPATH=src:. python3 -m pytest -q tests/
cd frontend && npx tsc --noEmit && npm run build
```
