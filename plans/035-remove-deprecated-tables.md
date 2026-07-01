# Plan 035: Remove deprecated tables — favorites, saved_jobs, evaluation_history

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise.

> **Drift check (run first)**: `git diff --stat 481ac71..HEAD -- db/schema.py db/favorites.py db/saved.py db/__init__.py db/stats.py db/evaluations.py api_server.py server/routes/jobs.py pipeline_db.py`
> If any in-scope file changed, compare excerpts against live code. Major mismatch → STOP.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: MED (large blast radius — 9 production files, 1 test file)
- **Depends on**: none
- **Category**: tech-debt
- **Planned at**: commit `481ac71`, 2026-06-30

## Why this matters

`favorites`, `saved_jobs`, and `evaluation_history` tables are marked DEPRECATED in `docs/DATA_MODEL.md` but have full code support across 9 production files. The replacement is the `decisions` table (already in schema, not yet wired). Agents reading the code will build on these tables. Tests create them. The API serves them. The CLI lists them. They must be removed so nobody accidentally depends on them.

## Current state

These tables exist and are actively used in code:

- `db/schema.py:71-78` — creates `favorites` table
- `db/schema.py:135-146` — creates `saved_jobs` and `evaluation_history` tables
- `db/favorites.py` — 38-line CRUD module
- `db/saved.py` — 31-line CRUD module
- `db/__init__.py:14-15` — exports favorites and saved_jobs functions
- `db/stats.py:13-14` — counts favorites and saved_jobs in get_stats()
- `db/evaluations.py:15` — writes to evaluation_history on re-evaluation
- `api_server.py:254-261` — GET /api/favorites endpoint
- `api_server.py:376-384` — POST /api/favorites/remove endpoint
- `server/routes/jobs.py:4,20-21` — imports favorites, hydrates job list with is_favorited/is_saved
- `pipeline_db.py:44,64-68,248-249,270` — favorites CLI action + status display
- `tests/test_jobs_pagination.py:55,61` — creates favorites/saved tables in test schema

Repo conventions:
- DB modules: raw sqlite3, no ORM. Patterns: `get_db()` returns connection, manual close().
- API server: stdlib `http.server`, routes in `server/routes/`, handlers registered in `api_server.py`.
- Tests: pytest with `tests/conftest.py` test_db fixture (temp SQLite, monkeypatch DB_PATH).
- Example module: `db/jobs.py` — clean CRUD with `get_db()`, context manager preferred but not enforced.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Run tests | `PYTHONPATH=. python3 -m pytest -q tests/` | all pass |
| Compile check | `PYTHONPATH=. python3 -m py_compile db/schema.py db/__init__.py db/stats.py db/evaluations.py api_server.py server/routes/jobs.py pipeline_db.py` | clean |

## Scope

**In scope**:
- `db/favorites.py` — DELETE entire file
- `db/saved.py` — DELETE entire file
- `db/schema.py` — remove favorites, saved_jobs, evaluation_history table creation
- `db/__init__.py` — remove favorites/saved exports
- `db/stats.py` — remove favorites/saved counts
- `db/evaluations.py` — remove evaluation_history write
- `api_server.py` — remove /api/favorites, /api/saved endpoints
- `server/routes/jobs.py` — remove favorites hydration from job list
- `pipeline_db.py` — remove favorites CLI action + status display
- `tests/test_jobs_pagination.py` — remove favorites/saved table creation

**Out of scope**:
- The `decisions` table — already exists in schema. Wiring it up is a separate Wave 6B plan.
- `evaluate/` agents — not related to these tables
- Dashboard React code — frontend may reference these endpoints; that's a separate plan

## Git workflow

- Commit: `git commit -m "remove deprecated tables: favorites, saved_jobs, evaluation_history"`
- Do NOT push unless instructed

## Steps

### Step 1: Delete the two CRUD module files

```bash
git rm db/favorites.py db/saved.py
```

**Verify**: `test -f db/favorites.py && echo "EXISTS" || echo "DELETED"` → DELETED for both

### Step 2: Remove table creation from db/schema.py

Open `db/schema.py`. Find and remove three blocks:

1. The `CREATE TABLE IF NOT EXISTS favorites` block (looks like lines 71-78)
2. The `CREATE TABLE IF NOT EXISTS saved_jobs` block
3. The `CREATE TABLE IF NOT EXISTS evaluation_history` block

Each is about 8-10 lines including the comment header. Remove the full block including the preceding comment line.

**Verify**: `grep -c "favorites\|saved_jobs\|evaluation_history" db/schema.py` → 0

### Step 3: Remove exports from db/__init__.py

Remove these imports:
```python
from db.favorites import add_favorite, remove_favorite, get_favorites
from db.saved import save_job, unsave_job, get_saved_jobs
```

**Verify**: `grep -c "favorite\|saved_job\|get_saved" db/__init__.py` → 0

### Step 4: Remove stats counters from db/stats.py

Find the stats dictionary builder. Remove counts for favorites and saved_jobs (lines adding `'favorites': ...` and `'saved': ...`).

**Verify**: `grep -c "favorites\|saved" db/stats.py` → 0

### Step 5: Remove evaluation_history write from db/evaluations.py

Find the line that inserts into `evaluation_history` (around line 15) and remove it. It's typically inside `save_evaluation()` or similar. Remove only the INSERT statement, not the entire function.

**Verify**: `grep -c "evaluation_history" db/evaluations.py` → 0

### Step 6: Remove API endpoints from api_server.py

Remove these endpoint registrations:
- `GET /api/favorites` — endpoint handler
- `POST /api/favorites/remove` — endpoint handler
- `GET /api/saved` — endpoint handler (if exists)

Also remove the import of favorites/saved modules if they were imported at the top.

**Verify**: `grep -c "favorites\|saved" api_server.py` → 0

### Step 7: Remove favorites hydration from server/routes/jobs.py

Remove the import of favorites/saved functions and the code that adds `is_favorited` and `is_saved` fields to job list responses. Keep the rest of the jobs route intact.

**Verify**: `grep -c "favorite\|saved\|is_favorited\|is_saved" server/routes/jobs.py` → 0

### Step 8: Remove CLI action from pipeline_db.py

Remove:
- `action_favorites()` function (entire function)
- `elif action == "favorites":` in dispatch table
- `s['favorites']` and `s['saved']` from the status display string (just remove those two interpolations, keep the rest)

**Verify**: `grep -c "favorite\|saved" pipeline_db.py` → 0

### Step 9: Update tests

In `tests/test_jobs_pagination.py`, remove the lines that create favorites and saved_jobs tables in the test schema setup.

**Verify**: `grep -c "favorites\|saved_jobs" tests/test_jobs_pagination.py` → 0

### Step 10: Run full test suite

**Verify**: `PYTHONPATH=. python3 -m pytest -q tests/` → all pass

### Step 11: Compile check all modified files

**Verify**: `PYTHONPATH=. python3 -m py_compile db/schema.py db/__init__.py db/stats.py db/evaluations.py api_server.py server/routes/jobs.py pipeline_db.py` → clean (no output)

### Step 12: Commit

**Verify**: `git status --short` shows only the expected modified files, then:
`git add -A && git commit -m "remove deprecated tables: favorites, saved_jobs, evaluation_history"` → exit 0

## Done criteria

- [ ] `db/favorites.py` and `db/saved.py` deleted
- [ ] No references to favorites, saved_jobs, or evaluation_history in any production .py file
- [ ] No favorites/saved API endpoints remain
- [ ] `PYTHONPATH=. python3 -m pytest -q tests/` — all pass
- [ ] `py_compile` on all modified files — clean

## STOP conditions

Stop and report back if:

- Any file outside scope shows as modified after changes
- Test suite fails and can't be fixed within 2 attempts
- A test references favorites/saved in a non-obvious way (e.g., `from db.favorites import ...` in a test file not listed above)

## Maintenance notes

The `decisions` table already exists in the schema but has no writers. A future plan (Wave 6B) will wire it up. Until then, user curation has no code path — jobs can only be evaluated and auto-packed, not marked as applied/skipped/rejected. This is intentional — the decision loop is part of the product build, not cleanup.
