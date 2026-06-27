# Plan 006: Batch job-list metadata queries

> **Executor instructions**: Follow this plan step by step. Run every verification command and confirm expected results. Stop on any STOP condition.
>
> **Drift check (run first)**: `git diff --stat b725a33..HEAD -- server/routes/jobs.py db/favorites.py db/decisions.py tests`

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: MED
- **Depends on**: plans/001-restore-verification-baseline.md
- **Category**: performance / tech-debt
- **Planned at**: commit `b725a33`, 2026-06-27

## Why this matters

The dashboard polls `/api/jobs` every 30 seconds. Today `list_jobs()` opens/query SQLite per job for favorite state and latest auto-apply decision. As job history grows, the main review UI becomes slower and noisier exactly where Arinze needs quick triage.

## Current state

Relevant files:
- `server/routes/jobs.py` — hydrates jobs for API.
- `db/favorites.py` — favorite helpers.
- `db/decisions.py` — decision event helpers.
- Tests: `tests/test_role_family_backfill_api.py` covers current auto-apply semantics.

Current excerpts:
- `server/routes/jobs.py:8-49`: loops jobs and calls `db_favs.is_favorite(r["id"])` plus `_is_auto_apply_enabled(r["id"])` for each row.
- `db/favorites.py:35-39`: `is_favorite()` opens a DB connection and queries one job.
- `server/routes/jobs.py:52-63`: `_is_auto_apply_enabled()` calls `db_decs.get_decisions(int(job_id))` and scans latest events.
- `db/decisions.py:15-21`: `get_decisions()` opens a DB connection and returns all decisions for one job ordered by id desc.
- `dashboard/src/App.tsx:33-35`: shared data hook polls every 30 seconds.

Important behavior:
- Auto-apply latest decision wins. The latest `auto_apply` or `auto_apply_remove` by descending decision id decides current state.

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| API behavior tests | `python3 -m pytest tests/test_role_family_backfill_api.py tests/test_audit_regressions.py -q` | exit 0 |
| Full tests | `python3 -m pytest -q` | exit 0 |
| Python syntax | `python3 -m py_compile $(find . -path './dashboard/node_modules' -prune -o -path './.git' -prune -o -path './.venv' -prune -o -name '*.py' -print)` | exit 0 |

## Scope

In scope:
- `server/routes/jobs.py`
- `db/favorites.py`
- `db/decisions.py`
- Tests for list job hydration semantics

Out of scope:
- Changing decision event schema.
- Changing dashboard polling interval.
- Adding caching that can go stale.

## Git workflow

- Branch suggestion: `advisor/006-batch-job-list-metadata`

## Steps

### Step 1: Add batch favorite lookup

Add a DB helper that returns all favorited job ids as a set/list using one connection/query. You may reuse existing `get_favorites()` if its behavior is enough. In `list_jobs()`, compute `favorite_ids` once and hydrate `isFavorite` using membership.

Verify existing favorite behavior through tests or add a small test if no coverage exists.

### Step 2: Add batch latest auto-apply lookup

Add a helper in `db/decisions.py` such as `get_latest_auto_apply_states(job_ids: Iterable[int]) -> dict[int, bool]`.

Implementation requirements:
- Only consider decisions in `('auto_apply', 'auto_apply_remove')`.
- Latest event by `id DESC` wins, not timestamp. This is already a known requirement because SQLite timestamps can tie.
- Jobs with no auto-apply decision should default false.

Use a portable SQLite query. If using a subquery, make it readable. Avoid clever SQL that future maintainers cannot debug.

Verify: extend `tests/test_role_family_backfill_api.py::test_list_jobs_exposes_current_auto_apply_toggle_state` or add a new test with enable → disable → enable sequences.

### Step 3: Hydrate jobs without per-row DB calls

Refactor `server/routes/jobs.py:list_jobs()` to:
- Fetch raw jobs once.
- Build `favorite_ids`, `saved_ids`, and `auto_apply_states` once.
- Loop rows and use those maps/sets.

Do not change response field names.

Verify focused tests and full tests.

## Test plan

- Preserve latest auto-apply semantics with multiple decisions in same second.
- Preserve favorite/saved state in list response.
- Optional: monkeypatch helpers or use query counter only if easy; do not overcomplicate.

## Done criteria

- [ ] `list_jobs()` no longer calls `is_favorite()` or `get_decisions()` inside the per-job loop.
- [ ] Latest auto-apply by decision id remains correct.
- [ ] Response shape from `/api/jobs` is unchanged.
- [ ] Focused API tests pass.
- [ ] `python3 -m pytest -q` exits 0.
- [ ] Python compile command exits 0.
- [ ] `plans/README.md` row 006 updated when done.

## STOP conditions

Stop and report if:
- SQLite version on Archilles cannot support the chosen grouped query.
- Auto-apply semantics are ambiguous for decisions other than `auto_apply` and `auto_apply_remove`.

## Maintenance notes

This plan should reduce DB work without adding caching. Reviewers should check readability of the query and that id ordering is used, not timestamps.
