# Plan 018: Split raw discovered jobs from evaluated job outcomes in SQLite

> Executor: depends on Plans 015 and 017. Do not change pack generation here.
>
> Drift check: `git diff --stat 451ea6a..HEAD -- db/schema.py db/jobs.py db/evaluations.py pipeline_db.py server/routes/jobs.py tests/`

## Status

- Priority: P1
- Effort: M
- Risk: MED
- Depends on: 015, 017
- Category: database / architecture
- Planned at: commit `451ea6a`, 2026-06-28

## Why this matters

The design separates the raw job universe from evaluated outcomes. A discovered job should stay as a source artifact with URL/company/JD/ATS/raw payload. Evaluation is a later derived result, with fit report, level, agent, pack path, and report inclusion. Current schema mixes raw job fields, classification fields, evaluation status, pack status, and review status into `jobs` plus `evaluations`.

## Current state

- `db/schema.py` has `jobs` with raw fields and derived workflow fields.
- `evaluations` already exists and is `job_id UNIQUE`, but it is not treated as the evaluated-jobs view/table.
- `evaluations.evaluated_by` defaults to `'hermes'`, not configured agent.
- Jobs table has `status`, `role_family`, `pack_status`, `outreach_status`, etc.

## Target design

Keep it lazy: do not do a destructive migration. Add/clarify tables:

- `discovered_jobs` from Plan 015 stores raw scraped/manual records.
- `jobs` can remain the canonical accepted job table for now.
- `evaluations` becomes the evaluated-job outcome table and gains enough fields for report/pack flow:
  - `agent`
  - `profile_snapshot_json`
  - `report_markdown`
  - `pack_dir`
  - `pack_template_id`
  - `cycle_id` or `report_cycle_id`

Do not duplicate all raw job fields into evaluations. Join when needed.

## Scope

In scope:
- `db/schema.py`
- `db/evaluations.py`
- API/list functions that need evaluation fields
- tests around evaluation save/read

Out of scope:
- Dashboard redesign
- Pack generation internals
- Report delivery implementation

## Steps

### Step 1: Extend evaluations table additively

In `db/schema.py`, add columns to new table definition and migration helper:
- `agent TEXT DEFAULT ''`
- `profile_snapshot_json TEXT DEFAULT '{}'`
- `report_markdown TEXT DEFAULT ''`
- `pack_dir TEXT DEFAULT ''`
- `pack_template_id TEXT DEFAULT ''`
- `report_cycle_id TEXT DEFAULT ''`

Add `_ensure_evaluation_columns(conn)` like `_ensure_jobs_columns(conn)`.

### Step 2: Update `db/evaluations.py`

Make `save_evaluation()` accept optional keys above. Preserve existing callers. Default `agent` to configured `EVALUATION_AGENT` if result doesn't include it.

### Step 3: Add tests

Update `tests/test_evaluation_writeback.py` or add `tests/test_evaluated_jobs_table.py`:
- saving evaluation stores fit fields
- saving evaluation stores `agent`
- saving evaluation stores `report_markdown` and `pack_dir` when provided
- old result dict without new keys still saves

### Step 4: Update API reads only if needed

If `server/routes/jobs.py` or dashboard expects pack/report data from `jobs`, add fields to existing response via joins. Avoid large UI changes.

## Done criteria

- Evaluations table has added fields in fresh and migrated DBs.
- `save_evaluation()` remains backward-compatible.
- New tests cover added fields.
- No raw job fields are duplicated into evaluations except references/derived report fields.
- `python3 -m pytest -q` passes.

## Stop conditions

Stop if this requires deleting/recreating `jobs`. This plan must be additive and safe.
