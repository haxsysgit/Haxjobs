# Changelog

All notable HaxJobs changes are tracked here.

HaxJobs uses version lines like `0.1.x`, `0.2.x`, and `0.3.x`.

Release policy:

- Every version slice should have its own commit.
- Subversions like `0.1.1` are tagged but do not get GitHub releases.
- Major line milestones like `0.1.0`, `0.2.0`, and `0.3.0` get GitHub releases.
- Major release notes should explain the product meaning, not just list changed files.

## 0.1.3 — Core CRUD APIs and manual job save

This version makes the model layer usable through the API.

It adds the first feature-based routers/repositories for saving jobs, creating profile records, storing reusable answers, and creating Hermes task requests.

Landed:

- `POST /api/jobs/manual` for manually saving a job before browser extensions exist.
- `GET /api/jobs` and `GET /api/jobs/{job_id}`.
- `POST /api/profiles` and `GET /api/profiles`.
- `POST /api/profiles/{profile_id}/facts`.
- `POST /api/profiles/{profile_id}/answers`.
- `POST /api/hermes-tasks`.
- Manual job save now creates a Job, optional Application, source Snapshot, and StatusEvent together.

Product meaning:

- HaxJobs can now accept real job-search state through HTTP instead of only models/tests.
- Hermes has the first API surface for queueable work.
- The manual-save workflow lets development continue before the browser extension lands.

## 0.1.2 — Core data models

This version adds the first complete HaxJobs data shape using SQLAlchemy 2.0 models and Pydantic schemas.

It matters because the product is now backed by the entities Hermes will actually need: user profile facts, saved application answers, jobs, snapshots, applications, packs, documents, contacts, outreach messages, Hermes tasks, approval checkpoints, and status events.

Architecture direction:

- Feature-based backend modules under `backend/haxjobs_api/features/`.
- SQLAlchemy 2.0 typed ORM models.
- Pydantic schemas beside feature models.
- Alembic migration for the core table set.

Product meaning:

- HaxJobs can now persist the core objects needed for the job-search workflow.
- Hermes has a real target shape for future task queue inputs and structured writebacks.
- Sensitive user answers can be modeled with review/approval sensitivity instead of being treated as plain text.

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
