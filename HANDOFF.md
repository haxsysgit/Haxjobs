# Handoff

**Plans 038 and 040 are DONE.** Commit: `6d65912`.

- 038: README shows "Under construction — come back when v1.0.0 ships"
- 040: Repo restructured as installable `uv` + `hatchling` package under `src/haxjobs/`. 255 tests pass. `uv build` creates wheel. `uv run haxjobs --help` works.

**Next: Plan 041** — FastAPI backend with feature-based structure (`features/{jobs,onboarding,discovery,etc}/routes.py + schemas.py + service.py`), uvicorn runner, serves frontend at `/dist`.

**Working dir:** `/home/hax/haxjobs` (renamed from `haxjobs-private-dev` mid-session — that's why bash broke).

**Exit** `/exit` then `pi` to restart.
