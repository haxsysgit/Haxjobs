# Handoff

**Plans 038, 040, 041 are DONE.** Commits: `6d65912` (040), `6929976` (041), `8d3ecc5` (mark).

- 038: README shows "Under construction — come back when v1.0.0 ships"
- 040: Repo restructured as installable `uv` + `hatchling` package under `src/haxjobs/`
- 041: FastAPI backend — `app.py` with lifespan DB init, feature-based structure under `features/` (7 modules), `server/main.py` uvicorn runner. 255 tests pass.

FastAPI endpoints all 200: `/api/health`, `/docs`, `/api/jobs` (live DB), `/api/jobs/:id` (404 for missing). 9 OpenAPI paths.

**Note:** Plan 040's `force-include` section is NOT needed. Hatchling auto-includes all files under `src/haxjobs/`. Adding it causes duplicate-file build errors. Wheel builds clean without it.

**Next: Plan 042** — Provider setup (first-run API key + model config).

**Working dir:** `/home/hax/haxjobs`
