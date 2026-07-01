# Plan 045: Discovery API — scraper endpoints, run from UI

> **Depends on**: 041 | **Priority**: P1 | **Effort**: M | **Risk**: LOW
> **Planned at**: commit `bf83142`, 2026-06-30

## Why this matters

Discovery currently runs via CLI (`pipeline_db.py discover-run`). The user should trigger discovery from the dashboard and see results stream in. This plan wraps existing scrapers in FastAPI endpoints.

## Steps

1. Create `src/haxjobs/server/routes/discovery.py` with:
   - `POST /api/discovery/run` — triggers all scrapers (Greenhouse, Ashby, Lever), returns job count
   - `GET /api/discovery/status` — returns current run status (running/done/error + count so far)
   - `GET /api/discovery/jobs/new` — returns newly discovered jobs since last check
2. Background task runner for discovery (don't block the request — fire and poll)
3. Wire existing `discovery/scrapers/orchestrator.py` into the endpoint
4. Add "Discover Jobs" button to frontend dashboard page

**Ponytail note**: Keep using existing scraper code from `discovery/scrapers/`. Only change is the trigger mechanism (CLI → API endpoint).

## Done criteria

- [ ] `POST /api/discovery/run` returns `{"status": "started", "job": "running"}`
- [ ] `GET /api/discovery/status` returns `{"running": true, "found": 47}`
- [ ] New jobs appear in DB after discovery completes
- [ ] Frontend dashboard has "Discover Jobs" button that calls the API
