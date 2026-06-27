# Plan 005: Persist generated pack directory

> **Executor instructions**: Follow this plan step by step. Run every verification command and confirm expected results. If a STOP condition occurs, stop and report.
>
> **Drift check (run first)**: `git diff --stat b725a33..HEAD -- db/schema.py db/jobs.py generate_ready_packs.py server/routes/jobs.py server/routes/outreach.py dashboard/src tests`

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: MED
- **Depends on**: plans/001-restore-verification-baseline.md, plans/004-enforce-approval-state-transitions.md
- **Category**: correctness
- **Planned at**: commit `b725a33`, 2026-06-27

## Why this matters

Manual pack generation returns a `pack_dir` immediately, but the jobs table persists only `pack_status`. After a dashboard reload, the UI knows a pack exists but cannot reliably link to or review it. Pack review is central to the approval-gated workflow, so generated pack location should be durable state.

## Current state

Relevant files:
- `db/schema.py` — jobs table and additive migrations.
- `db/jobs.py` — job update helpers.
- `generate_ready_packs.py` — generates packs and marks status.
- `server/routes/jobs.py` — `list_jobs()` exposes `packDir` from DB row.
- `server/routes/outreach.py` — outreach types/UI expect pack details but route does not select `pack_dir` yet.
- `dashboard/src/pages/JobDetail.tsx` and `dashboard/src/pages/Outreach.tsx` — show pack links only when `packDir` exists.

Current excerpts:
- `db/schema.py:21-44`: jobs table has `pack_status` but no `pack_dir` column.
- `db/schema.py:181-204`: `_ensure_jobs_columns()` adds reset-era columns but not `pack_dir`.
- `db/jobs.py:76-80`: `update_job_pack_status(job_id, pack_status)` writes only status.
- `generate_ready_packs.py:107-120`: `generate_pack_for_job()` gets `result["pack_dir"]`, updates status, returns directory in response.
- `server/routes/jobs.py:37-38`: API returns `"packDir": r.get("pack_dir", "")` even though schema does not create it.
- `dashboard/src/pages/JobDetail.tsx:100-107`: UI shows pack location only if `job.packDir` exists.

Repo conventions:
- Schema migrations are additive and idempotent using `_ensure_jobs_columns()`.
- Tests use temp DB monkeypatches and should not hit live Archilles DB.

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| Pack generation tests | `python3 -m pytest tests/test_manual_pack_generation.py tests/test_generate_ready_packs.py -q` | exit 0 |
| Role/schema tests | `python3 -m pytest tests/test_role_family_db.py tests/test_role_family_backfill_api.py -q` | exit 0 |
| Full tests | `python3 -m pytest -q` | exit 0 |
| Dashboard typecheck | `cd dashboard && npx tsc -b --noEmit` | exit 0 |

## Scope

In scope:
- `db/schema.py`
- `db/jobs.py`
- `generate_ready_packs.py`
- `server/routes/jobs.py`
- `server/routes/outreach.py`
- Dashboard type/interface updates if API shape changes
- Tests under `tests/`

Out of scope:
- Moving pack files.
- Backfilling every historical pack from live Archilles unless the operator explicitly runs a migration there.
- Changing pack content.

## Git workflow

- Branch suggestion: `advisor/005-persist-pack-dir`

## Steps

### Step 1: Add `pack_dir` as an additive jobs column

Update `db/schema.py`:
- Add `pack_dir TEXT DEFAULT ''` to new `CREATE TABLE jobs` definition.
- Add `"pack_dir": "TEXT DEFAULT ''"` to `_ensure_jobs_columns()`.
- Consider an index only if queries will filter by pack dir; likely not needed.

Add/extend tests so temp DB schema includes `pack_dir`, and older DB migration adds it.

Verify: `python3 -m pytest tests/test_role_family_db.py -q` → exit 0.

### Step 2: Persist pack directory when generation succeeds

Update DB helper(s) to set both `pack_status` and `pack_dir`. Options:
- Change `update_job_pack_status(job_id, pack_status, pack_dir=None)` to set `pack_dir` when provided.
- Or add `update_job_pack_result(job_id, pack_status, pack_dir)` and use it in generation paths.

Update both `generate_ready_packs()` and `generate_pack_for_job()` to persist `result["pack_dir"]` after `build_job_pack()` succeeds.

Verify: `python3 -m pytest tests/test_manual_pack_generation.py tests/test_generate_ready_packs.py -q` → exit 0.

### Step 3: Return packDir consistently from APIs

`server/routes/jobs.py:list_jobs()` already tries to return `packDir`; confirm it works after schema change.

Update `server/routes/outreach.py` to select and return `j.pack_dir` if the Outreach UI expects `packDir`. Its TypeScript interfaces already include `packDir`, but the route currently selects `j.outreach_status`, `j.pack_status`, etc. without `pack_dir`.

Verify dashboard typecheck after API type updates.

### Step 4: Add safe historical backfill helper only if needed

If tests or code need pack_dir for existing generated packs, add a small helper that can infer pack directory from `packs/<job_id>_*`. Keep it opt-in, deterministic, and covered by tests. Do not run it on live Archilles in this plan unless explicitly instructed.

## Test plan

Add/extend tests for:
- Schema creates and migrates `pack_dir`.
- Manual pack generation persists pack status and pack directory.
- Ready pack generation persists pack directory.
- `list_jobs()` exposes `packDir` after generation.
- Outreach route returns `packDir` if drafts/jobs have it.

## Done criteria

- [ ] Jobs schema includes additive `pack_dir` column.
- [ ] Pack generation persists `pack_dir` with `pack_status`.
- [ ] `/api/jobs` returns stable `packDir` after reload/list.
- [ ] Outreach API returns `packDir` where UI expects it.
- [ ] Focused tests pass.
- [ ] `python3 -m pytest -q` exits 0.
- [ ] Dashboard typecheck exits 0.
- [ ] No runtime pack files are moved or committed.
- [ ] `plans/README.md` row 005 updated when done.

## STOP conditions

Stop and report if:
- Existing production DB has conflicting `pack_dir` semantics.
- Pack directory cannot be safely represented repo-relative vs absolute. Prefer repo-relative if possible; otherwise document the choice.
- Backfill would require scanning private/runtime pack contents.

## Maintenance notes

Reviewers should check that pack review UI does not depend only on local optimistic state. Generated pack location must survive a server restart and dashboard reload.
