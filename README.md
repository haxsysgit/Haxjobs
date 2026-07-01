# HaxJobs

A self-hosted job search platform. Upload your CV, answer a few questions, and HaxJobs discovers jobs, evaluates fit, generates application packs, and gets smarter the more you use it.

## How it works

1. **Onboard** — upload CV, LLM extracts your profile, targeted questions fill gaps (~10 min)
2. **Discover** — web search + ATS scrapers find jobs matching your profile
3. **Evaluate** — direct LLM API calls score every job against your full profile
4. **Pack** — auto-generated CV reviews and cover letters for good fits
5. **Decide** — apply, skip, or reject from the dashboard — the system learns
6. **Outreach** — find hiring managers, draft personalized messages

## Architecture

Web UI (React) → API Server (Python) → Pipeline Engine → SQLite

Read `docs/PRODUCT_ARCHITECTURE.md` for the full vision and component design.

## Quick start

```bash
# (future — currently requires manual setup)
pip install haxjobs
haxjobs start              # opens http://localhost:8241
```

## Config

`haxjobs.toml` is the canonical config. `haxjobs_config.py` is a thin parser. Env vars override. Nothing is hardcoded.

## Docs

| Doc | Audience |
|-----|----------|
| `AGENTS.md` | Coding agents working in this repo |
| `docs/PRODUCT_ARCHITECTURE.md` | Full product vision and component design |
| `docs/ARCHITECTURE.md` | Technical architecture reference |
| `docs/DATA_MODEL.md` | Database schema |
| `docs/HAXJOBS_PRODUCT_SPEC.md` | Original 2026-06-11 product spec (historical) |
| `plans/README.md` | Implementation plans and status |

## Development

```bash
./dev-app.sh start                     # backend + frontend
PYTHONPATH=. python3 -m pytest -q tests/   # tests (PYTHONPATH required)
```

## What's not committed

`intake/`, `packs/`, `state/`, `reports/`, `outreach/`, SQLite databases, `.env` files, LinkedIn cookies, `node_modules/`, Vite build artifacts.
