# Plan 045: Discovery API — scraper endpoints, run from UI

> **Depends on**: 041 | **Priority**: P1 | **Effort**: M | **Risk**: LOW
> **Planned at**: commit `bf83142`, 2026-06-30

## Why this matters

Discovery runs via CLI (`pipeline_db.py discover-run`). Should be triggerable from dashboard and show results streaming. This plan fills `features/discovery/` — wraps existing scraper code in API endpoints.

## Steps

### Backend: features/discovery/

1. **schemas.py**: `DiscoveryRunResponse`, `DiscoveryStatusResponse`, `DiscoveredJobResponse`
2. **service.py**:
   - `run_discovery() -> str` — calls `discovery.scrapers.orchestrator.run_all()`, returns run_id
   - `get_status() -> dict` — returns {running: bool, found: int, errors: list}
   - `get_new_jobs(since: str) -> list` — returns jobs discovered since timestamp
3. **routes.py**:
   - `POST /api/discovery/run` — triggers scrapers, returns run_id
   - `GET /api/discovery/status` — returns current run status
   - `GET /api/discovery/jobs/new` — new jobs since last check

### Frontend

4. Add "Discover Jobs" button to DashboardPage. Calls `POST /api/discovery/run`, polls status, shows new job count on completion.

## Done criteria

- [ ] `POST /api/discovery/run` returns run_id
- [ ] `GET /api/discovery/status` shows running state + found count
- [ ] New jobs appear in DB after discovery
- [ ] Dashboard has discover button

## STOP conditions

- Scrapers fail with auth errors — the configured companies may have changed their API. Test with one scraping company first.
- Long-running scrape blocks the request — use background task (threading.Thread or asyncio.create_task)
