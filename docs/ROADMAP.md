# HaxJobs Roadmap

The authoritative roadmap is `plans/README.md` — it contains the execution order, dependencies, and status for all implementation plans.

## Pipeline wave (plans 015-019) — DONE

All five pipeline plans are implemented and live on main:

1. **015 — Discovery ingestion spine** — discovered_jobs table, normalize.py, hooks.py, CLI
2. **016 — Config contract expansion** — haxjobs.toml sections, 10 config constants
3. **017 — Config-driven classification + pluggable evaluation** — role_family.py reads TOML, evaluate/agents/ package
4. **018 — Evaluation state split** — evaluations table with agent, pack, report columns
5. **019 — Auto-pack L1/L2 + cycle report** — template fill, generate_cycle_report.py

## Discovery scrapers (plans 023-024)

- **023 — Greenhouse scraper** — DONE. Live, config-driven, filters through hooks.
- **024 — Ashby, Lever, LinkedIn scrapers + orchestrator** — IN PROGRESS (Hermes).

## Architecture polish (plans 025-026)

- **025 — Root cleanup** — delete stale files, fix docs, rewrite .env.example
- **026 — Unified automation** — refactor pipeline_db.py, add discover-full/run-full, wire cron

## Future

- **027 — Typed CV validation hook** — validate generated CV output against profile to prevent LLM hallucination (from CV_FRAME_GOVERNANCE concept)
- **3-Agent Simulation Loop (v0.3)** — coaching simulation: Recruiter → Applicant → Evaluator

Output: `packs/<job>/simulation.json`. Max 3 rounds.

## Completed

Plans 001-014 (cleanup wave 1) — all DONE. See `plans/README.md` for details.
