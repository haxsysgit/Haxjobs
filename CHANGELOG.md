# Changelog

All notable HaxJobs changes are tracked here.

HaxJobs uses version lines like `0.1.x`, `0.2.x`, and `0.3.x`.

Release policy:

- Every version slice should have its own commit.
- Subversions like `0.1.1` are tagged but do not get GitHub releases.
- Major line milestones like `0.1.0`, `0.2.0`, and `0.3.0` get GitHub releases.
- Major release notes should explain the product meaning, not just list changed files.

## 0.1.1 — Database foundation and local persistence baseline

This version adds the first real persistence layer for HaxJobs.

It matters because HaxJobs is meant to be Hermes's durable job-search surface, not just a temporary UI. Jobs, profile facts, applications, packs, generated documents, Hermes tasks, and approval checkpoints all need a database-backed home before the bigger workflow can become reliable.

Landed:

- SQLAlchemy engine/session setup.
- SQLite local default for early development.
- Alembic migration setup.
- Initial baseline migration.
- Local `data/` and `data/documents/` placeholders.
- Backend tests proving database connectivity and migration availability.

Product meaning:

- HaxJobs now has a storage foundation for later data models.
- The project can evolve through migrations instead of one-off local files.
- Future Hermes writebacks have a real persistence layer to target.

## 0.1.0 — Project skeleton and local app shell

This version turns HaxJobs from product direction into a runnable local app skeleton.

It establishes the split that will matter throughout the project:

- FastAPI owns backend APIs, persistence, and Hermes-facing workflow state.
- Vue owns the human dashboard, review surface, and profile/survey UI.
- Hermes remains the heavy reasoning/automation layer.

Landed:

- FastAPI backend app.
- `/health` endpoint.
- Vue 3 + Vite frontend created with `create-vue`.
- Frontend API client for backend health checks.
- Basic local setup documentation.
- Separate backend/frontend dev scripts.

Product meaning:

- Backend and frontend can run locally.
- The frontend can confirm the backend is alive.
- The repo has a clean foundation for the `0.1.x` build line.

## Earlier experimental history

This repository may still contain older exploratory commits/tags from the previous HaxJobs prototype history. The current rebuild path is documented in `docs/ROADMAP.md` and starts from the new `0.1.x` foundation line.
