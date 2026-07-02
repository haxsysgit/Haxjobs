# Plan 047: Discovery API — scraper endpoints, run from UI

> **Depends on**: 041 | **Priority**: P1 | **Effort**: M | **Risk**: LOW
> **Planned at**: commit `bf83142`, 2026-06-30

> ⚠️ **PLANS ARE NOT FINAL** — review against current project reality before implementing.
> Every plan was drafted at a point in time. File paths, function signatures, dependency
> versions, and architecture decisions may have changed since. If the plan says
> `run_structured()` but the codebase has `run() + extract_json()`, follow the codebase.
> If the plan references a deleted file, skip that step. Use these plans as guidance,
> not gospel.

## Why this matters

Discovery runs via CLI (`pipeline_db.py discover-run`). Should be triggerable from dashboard and show results streaming. This plan fills `features/discovery/` — wraps existing scraper code in API endpoints.

Plan 043 adds agentic discovery tools (`web_search`, `fetch_page`, read-only `db_query`). This API plan can still ship with existing scrapers only. If the executor adds agentic discovery, allow only discovery/read-only tools here — not `bash`, `write`, or `edit`.

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
- [ ] If agentic discovery is enabled, its tool allowlist excludes `bash`, `write`, and `edit`

## Deliverable report (required)

After implementation, the executor must produce a compact report:

- **What changed**: files created, modified, deleted
- **Deliverables**: endpoints, pages, CLI commands the user can now use
- **How to verify**: the exact commands that prove it works
- **Deviations from plan**: what the plan said vs what was actually done
- **What was skipped**: and the reason (YAGNI, blocked, deferred)

## STOP conditions

- Scrapers fail with auth errors — the configured companies may have changed their API. Test with one scraping company first.
- Long-running scrape blocks the request — use background task (threading.Thread or asyncio.create_task)
