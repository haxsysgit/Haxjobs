# HaxJobs Roadmap

The authoritative roadmap is `plans/README.md` — it contains the execution order, dependencies, and status for all implementation plans.

## Current wave: Pipeline implementation (plans 015-019)

Execute in order:

1. **015 — Restore discovery-first ingestion** — scrapers → raw jobs → hooks → DB
2. **016 — Expand profile config contract** — haxjobs.toml sections for user, job_search, roles, evaluation, delivery
3. **017 — Profile-driven classification + pluggable evaluation** — classifier reads config, evaluate/ package with agent adapters
4. **018 — Split raw and evaluated job state** — discovered_jobs table, evaluations with agent/pack/report fields
5. **019 — Auto-pack and cycle report** — L1/L2 template fill, L3/L4 report-only, cycle markdown digest

## Cleanup wave (plans 020-022)

Run before implementations:

- **020 — Docs audit and alignment** — all .md files updated to match current vision
- **021 — Stale test cleanup** — delete tests for deleted code / wrong design
- **022 — Dead file sweep** — delete remaining unreferenced scripts

## Future: 3-Agent Simulation Loop (v0.3)

Designed, not yet implemented. After the pipeline produces packs, a coaching simulation stress-tests them:

- **Recruiter Agent** — plays hiring manager
- **Applicant Agent** — answers as Arinze from profile evidence
- **Evaluator Agent** — judges improvement, separates safe edits from fabrication

Output: `packs/<job>/simulation.json`. Max 3 rounds.

## Completed

Plans 001-014 (cleanup wave 1) — all DONE. See `plans/README.md` for details.
