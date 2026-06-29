# Plan 013: Add pagination to /api/jobs endpoint

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.

> **Drift check (run first)**: `git diff --stat 451ea6a..HEAD -- server/routes/jobs.py db/evaluations.py api_server.py dashboard/src/data/api.ts dashboard/src/pages/Pipeline.tsx`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: LOW
- **Depends on**: none
- **Category**: perf
- **Planned at**: commit `451ea6a`, 2026-06-28
- **Issue**: (none)

## Why this matters

The `/api/jobs` endpoint currently loads every job in the database into memory, joins with evaluations, then filters by status client-side. With even 200+ jobs, this is a full table scan per request. The dashboard calls this on every page load and when switching between status tabs. As the job count grows, response times will degrade linearly. Adding backend pagination (offset/limit) and server-side status filtering keeps the endpoint fast regardless of total job count.

## Current state

- `server/routes/jobs.py` — `list_jobs()` function (lines 8–59). Calls `db_evals.get_jobs_with_evaluations()` which loads ALL rows with a LEFT JOIN. No parameters for offset/limit.
- `db/evaluations.py` — `get_jobs_with_evaluations(status_filter=None)` (lines 66–83). Takes a status filter but no pagination params.
- `api_server.py` — `/api/jobs` handler (lines 214–219). Calls `list_jobs()`, then filters by status client-side.
- `dashboard/src/data/api.ts` — `api.getJobs(status?)` (lines 147–150). No offset/limit params.
- `dashboard/src/pages/Pipeline.tsx` — the main jobs list page. Uses `api.getJobs('pending')` etc. for status tabs.

The API route as it exists today (`api_server.py:214-219`):
```python
if path == "/api/jobs":
    status_filter = qs.get("status", [None])[0]
    jobs = list_jobs()
    if status_filter:
        jobs = [j for j in jobs if j["status"] == status_filter]
    self._json(jobs)
```

The `list_jobs()` function (`server/routes/jobs.py:8-59`):
```python
def list_jobs():
    """Return all jobs with evaluations, hydrated with favorites and auto-apply state.
    Uses batch lookups so the dashboard poll scales as O(1) DB round-trips
    regardless of how many jobs are in the system.
    """
    raw = db_evals.get_jobs_with_evaluations()
    # ... batch hydration of favorites, saved, auto_apply ...
    return result
```

The `get_jobs_with_evaluations` function (`db/evaluations.py:66-83`):
```python
def get_jobs_with_evaluations(status_filter=None):
    conn = get_db()
    query = """
        SELECT j.*, e.fit_score, e.fit_verdict, ...
        FROM jobs j
        LEFT JOIN evaluations e ON j.id = e.job_id
    """
    if status_filter:
        query += " WHERE j.status=?"
        rows = conn.execute(query + " ORDER BY j.discovered_at DESC",
                           (status_filter,)).fetchall()
    else:
        rows = conn.execute(query + " ORDER BY j.discovered_at DESC").fetchall()
    conn.close()
    return [_job_with_eval(r) for r in rows]
```

Repo conventions: API responses are plain JSON arrays (not wrapped in `{data: [...], total: N}`). The dashboard fetches jobs and stores them in React state. Query parameters use standard `?key=value` format, parsed by `parse_qs`. Python functions return `(status_code, data)` tuples or plain lists. Tests use temporary SQLite databases with monkeypatched paths.

## Commands you will need

| Purpose   | Command                  | Expected on success |
|-----------|--------------------------|---------------------|
| Python tests | `python3 -m pytest -q`   | 210+ passed         |
| Python compile | `python3 -m py_compile $(find . -path './dashboard/node_modules' -prune -o -path './.git' -prune -o -name '*.py' -print)` | exit 0 |
| Dashboard typecheck | `cd dashboard && npx tsc -b --noEmit` | exit 0 |
| Dashboard lint | `cd dashboard && npm run lint -- --quiet` | exit 0 |
| Dashboard build | `cd dashboard && npm run build` | exit 0 |
| Bash syntax | `bash -n cron/run_pipeline.sh scripts/haxjobs-update dashctl.sh build-dash.sh dev-watch.sh pack_builder.sh` | exit 0 |

## Scope

**In scope** (the only files you should modify):
- `db/evaluations.py` — add `offset`/`limit` params to `get_jobs_with_evaluations`
- `server/routes/jobs.py` — thread `offset`/`limit`/`status` through `list_jobs`
- `api_server.py` — parse new query params and pass them
- `dashboard/src/data/api.ts` — add optional params to `getJobs`
- `dashboard/src/pages/Pipeline.tsx` — add "Load more" button (minimal UI change)
- `tests/test_manual_pack_generation.py` or a new test file — add pagination tests

**Out of scope** (do NOT touch):
- Other API endpoints (packs, favorites, outreach, etc.) — paginate only `/api/jobs`
- The dashboard page layout or design — add only a "Load more" button, no redesign
- DB schema changes — no new indexes or columns
- Changing the batch hydration pattern (favorites/saved/auto_apply) — keep it as-is

## Git workflow

- Branch: `perf/013-api-jobs-pagination` off `main`
- Commit message style: imperative, e.g. `perf: add offset/limit pagination to /api/jobs`
- Do NOT push or open a PR unless instructed.

## Steps

### Step 1: Add pagination params to db/evaluations.py

Open `db/evaluations.py`. Modify `get_jobs_with_evaluations` to accept `offset` and `limit` parameters. The function currently has:

```python
def get_jobs_with_evaluations(status_filter=None):
```

Change the signature to:

```python
def get_jobs_with_evaluations(status_filter=None, offset=0, limit=None):
```

And add LIMIT/OFFSET to the SQL queries. After both ORDER BY clauses, append:

```python
    if limit is not None:
        query += " LIMIT ? OFFSET ?"
        params = (status_filter, limit, offset) if status_filter else (limit, offset)
    elif status_filter:
        params = (status_filter,)
    else:
        params = ()
```

The full modified function should look like:

```python
def get_jobs_with_evaluations(status_filter=None, offset=0, limit=None):
    conn = get_db()
    query = """
        SELECT j.*, e.fit_score, e.fit_verdict, e.level, e.level_name,
               e.strongest_matches, e.major_gaps, e.sponsorship_risk,
               e.summary, e.decision as eval_decision, e.skip_reason,
               e.role_type, e.evaluated_by, e.evaluated_at
        FROM jobs j
        LEFT JOIN evaluations e ON j.id = e.job_id
    """
    if status_filter:
        query += " WHERE j.status=?"
        query += " ORDER BY j.discovered_at DESC"
        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            rows = conn.execute(query, (status_filter, limit, offset)).fetchall()
        else:
            rows = conn.execute(query, (status_filter,)).fetchall()
    else:
        query += " ORDER BY j.discovered_at DESC"
        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            rows = conn.execute(query, (limit, offset)).fetchall()
        else:
            rows = conn.execute(query).fetchall()
    conn.close()
    return [_job_with_eval(r) for r in rows]
```

IMPORTANT: Backward compatibility — when called without `limit` (current behavior), it returns ALL rows. This keeps existing callers working without changes. Only when `limit` is provided does pagination activate.

**Verify**: `python3 -m pytest tests/test_manual_pack_generation.py -q` → existing tests pass (they call `get_jobs_with_evaluations()` without pagination params, confirming backward compat)

### Step 2: Thread pagination through list_jobs in server/routes/jobs.py

Open `server/routes/jobs.py`. Modify `list_jobs` to accept `status_filter`, `offset`, and `limit`:

```python
def list_jobs(status_filter=None, offset=0, limit=None):
    """Return jobs with evaluations, hydrated with favorites and auto-apply state.
    
    Accepts optional status_filter, offset, and limit for pagination.
    When limit is None (default), returns all jobs (backward compat).
    """
    raw = db_evals.get_jobs_with_evaluations(
        status_filter=status_filter, offset=offset, limit=limit
    )

    # Batch: gather all job IDs once
    job_ids = [r["id"] for r in raw]
    favorite_ids = set(db_favs.get_favorites())
    saved_ids = {s["id"] for s in db_saved.get_saved_jobs()}
    auto_apply_states = db_decs.get_latest_auto_apply_states(job_ids)

    result = []
    for r in raw:
        jid = r["id"]
        result.append({
            # ... same dict as before, no changes ...
        })
    return result
```

The dict construction inside the loop is unchanged — just copy the existing dict literal exactly. The only changes are the function signature and the call to `get_jobs_with_evaluations`.

**Verify**: `python3 -m pytest tests/test_manual_pack_generation.py -q` → tests pass (they call `list_jobs()` without args)

### Step 3: Update the API route in api_server.py

Open `api_server.py`. Modify the `/api/jobs` GET handler (lines 214–219) to parse pagination params and pass them through:

```python
if path == "/api/jobs":
    status_filter = qs.get("status", [None])[0]
    offset_str = qs.get("offset", ["0"])[0]
    limit_str = qs.get("limit", [None])[0]
    try:
        offset = max(0, int(offset_str))
    except (ValueError, TypeError):
        offset = 0
    try:
        limit = int(limit_str) if limit_str else None
    except (ValueError, TypeError):
        limit = None
    jobs = list_jobs(status_filter=status_filter, offset=offset, limit=limit)
    self._json(jobs)
```

Note: the client-side status filtering (`[j for j in jobs if j["status"] == status_filter]`) is REMOVED — the filtering now happens in the DB query.

**Verify**: `python3 -m pytest tests/test_api_security.py -q` → tests pass (they hit the API endpoint)

### Step 4: Add a test for pagination

Create `tests/test_jobs_pagination.py` with tests that verify pagination works correctly. Model after `tests/test_manual_pack_generation.py` which uses temp SQLite DBs:

```python
"""Pagination tests for /api/jobs endpoint."""
import json
import pytest
from pathlib import Path
from unittest.mock import patch

from db.schema import init as init_db, get_db
from db.jobs import insert_job
from db.evaluations import save_evaluation, get_jobs_with_evaluations
from server.routes.jobs import list_jobs


@pytest.fixture
def seeded_db(tmp_path, monkeypatch):
    """Create a temp DB with 25 jobs spanning different statuses."""
    db_path = tmp_path / "test.db"
    monkeypatch.setattr("haxjobs_config.DB_PATH", str(db_path))
    # Force reload so schema.init uses the monkeypatched path
    import importlib, haxjobs_config
    importlib.reload(haxjobs_config)
    import db.schema
    importlib.reload(db.schema)
    init_db()

    # Insert 25 jobs
    for i in range(25):
        status = "pending" if i < 10 else "evaluated" if i < 20 else "skipped"
        job_id = insert_job(
            title=f"Job {i}",
            company=f"Company {i}",
            location="London",
            source="test",
        )
        if job_id and status != "pending":
            # Manually update status (insert_job always sets 'pending')
            conn = get_db()
            conn.execute("UPDATE jobs SET status=? WHERE id=?", (status, job_id))
            conn.commit()
            conn.close()
        if job_id and status == "evaluated":
            save_evaluation(job_id, {
                "fit_score": 80 - i,
                "fit_verdict": "GOOD_FIT" if i < 15 else "SKIP",
                "level": 2,
                "level_name": "Quick Apply",
                "strongest_matches": [],
                "major_gaps": [],
                "sponsorship_risk": "low",
                "summary": f"Summary {i}",
                "decision": "completed",
                "skip_reason": "",
                "role_type": "backend",
                "evaluated_by": "test",
            })
            # save_evaluation changes status to 'evaluated' — fix that
            conn = get_db()
            conn.execute("UPDATE jobs SET status='evaluated' WHERE id=?", (job_id,))
            conn.commit()
            conn.close()


def test_pagination_returns_limited_results(seeded_db):
    result = list_jobs(limit=10, offset=0)
    assert len(result) == 10


def test_pagination_offset_returns_different_page(seeded_db):
    page1 = list_jobs(limit=10, offset=0)
    page2 = list_jobs(limit=10, offset=10)
    assert len(page1) == 10
    assert len(page2) == 10
    # No overlap between pages
    page1_ids = {j["id"] for j in page1}
    page2_ids = {j["id"] for j in page2}
    assert page1_ids.isdisjoint(page2_ids)


def test_pagination_with_status_filter(seeded_db):
    result = list_jobs(status_filter="pending", limit=5, offset=0)
    assert len(result) <= 5
    for job in result:
        assert job["status"] == "pending"


def test_no_limit_returns_all(seeded_db):
    result = list_jobs()
    assert len(result) == 25  # backward compat — all jobs
```

**Verify**: `python3 -m pytest tests/test_jobs_pagination.py -q` → all 4 tests pass

### Step 5: Update dashboard TypeScript API client

Open `dashboard/src/data/api.ts`. Modify `getJobs` to accept optional pagination params:

```typescript
getJobs: (status?: string, offset?: number, limit?: number) => {
    const params = new URLSearchParams()
    if (status) params.set('status', status)
    if (offset !== undefined) params.set('offset', String(offset))
    if (limit !== undefined) params.set('limit', String(limit))
    const qs = params.toString()
    return fetchAPI<Job[]>(`/api/jobs${qs ? '?' + qs : ''}`)
},
```

**Verify**: `cd dashboard && npx tsc -b --noEmit` → exit 0

### Step 6: Add "Load more" button to Pipeline page

Open `dashboard/src/pages/Pipeline.tsx`. This is a minimal change — add a constant `PAGE_SIZE = 50` and a "Load more" button at the bottom of the jobs list. The exact implementation depends on the current Pipeline page structure (which may vary). The key change:

1. Instead of calling `api.getJobs(statusFilter)`, call `api.getJobs(statusFilter, 0, displayedJobs.length + PAGE_SIZE)` when the "Load more" button is clicked.
2. Track `hasMore` state (true when the returned array length equals the requested limit, suggesting more may exist).

If the Pipeline page structure makes this complex, defer the frontend change to a separate plan and scope THIS plan to backend-only (steps 1–4). The backend pagination is useful even without a "Load more" button — it just won't be exercised by the dashboard yet.

**Decision point**: if adding the button requires restructuring the Pipeline component's data flow, SKIP this step. The backend is the important part. Document that the dashboard still fetches all jobs (no `limit` param = backward compat).

**Verify** (if implemented): `cd dashboard && npx tsc -b --noEmit && npm run lint -- --quiet && npm run build` → all exit 0

### Step 7: Full verification baseline

**Verify**:
- `python3 -m pytest -q` → 214+ tests pass (210 existing + 4 new pagination tests)
- `python3 -m py_compile $(find . -path './dashboard/node_modules' -prune -o -path './.git' -prune -o -name '*.py' -print)` → exit 0
- `cd dashboard && npx tsc -b --noEmit && npm run lint -- --quiet && npm run build` → all exit 0
- `bash -n cron/run_pipeline.sh scripts/haxjobs-update dashctl.sh build-dash.sh dev-watch.sh pack_builder.sh` → exit 0

## Test plan

New tests in `tests/test_jobs_pagination.py`:
1. `test_pagination_returns_limited_results` — limit=10 returns exactly 10 jobs
2. `test_pagination_offset_returns_different_page` — offset=10 returns different jobs than offset=0
3. `test_pagination_with_status_filter` — status filter + pagination work together
4. `test_no_limit_returns_all` — backward compat: no limit arg returns all 25 jobs

Model after `tests/test_manual_pack_generation.py` for temp DB setup pattern.

## Done criteria

ALL must hold:

- [ ] `python3 -m pytest -q` exits 0, 214+ tests pass
- [ ] `db/evaluations.py` function `get_jobs_with_evaluations` has `offset` and `limit` parameters
- [ ] `server/routes/jobs.py` function `list_jobs` has `status_filter`, `offset`, `limit` parameters
- [ ] `api_server.py` parses `offset` and `limit` query params from `/api/jobs`
- [ ] Backward compat: calling `list_jobs()` with no args returns all jobs (tested)
- [ ] Dashboard typecheck/lint/build pass
- [ ] No files outside the in-scope list modified

## STOP conditions

Stop and report back (do not improvise) if:
- The DB pagination test fixture can't create jobs (may need to adapt to the actual `insert_job` / `save_evaluation` behavior around status transitions)
- `save_evaluation` auto-updates `jobs.status` to `'evaluated'` — the test fixture must account for this (as shown in step 4)
- Any pre-existing test breaks due to the signature change (should not happen — all new params have defaults)
- The dashboard Pipeline page has a radically different structure than expected — skip step 6

## Maintenance notes

- The pagination is offset-based, not cursor-based. For datasets under 1000 jobs, this is fine and simpler. If the job count eventually exceeds 1000, consider cursor-based pagination using `discovered_at` or `id`.
- The `list_jobs` function still does client-side hydration of favorites/saved/auto_apply for the returned batch only — this is efficient since the batch is small (50–100 items).
- Future plan: add a `GET /api/jobs/count?status=pending` endpoint so the dashboard can show "Page 1 of N" without loading all jobs.
