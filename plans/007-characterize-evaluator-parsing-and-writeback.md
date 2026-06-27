# Plan 007: Characterize evaluator parsing and writeback

> **Executor instructions**: Follow this plan step by step. Run every verification command and confirm expected results. Stop on any STOP condition.
>
> **Drift check (run first)**: `git diff --stat b725a33..HEAD -- evaluate_with_hermes.py db/evaluations.py cron/sync_db_to_intake.py tests`

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: MED
- **Depends on**: plans/001-restore-verification-baseline.md
- **Category**: tests / correctness
- **Planned at**: commit `b725a33`, 2026-06-27

## Why this matters

The evaluator is the central job-ranking path. It parses Hermes CLI output, validates JSON, writes SQLite evaluations, updates job status, and still mirrors data into intake JSON. Before larger SQLite-source-of-truth refactors, this behavior needs characterization tests so cleanup does not silently break scoring or status transitions.

## Current state

Relevant files:
- `evaluate_with_hermes.py` — evaluator prompt, JSON extraction, Hermes call, DB/intake writeback.
- `db/evaluations.py` — saves evaluation result and updates job status.
- `tests/test_evaluator_pack_prompt.py` — currently only checks prompt wording around reusable CV variants.

Current excerpts:
- `evaluate_with_hermes.py:188-233`: `extract_json()` handles Hermes box output, fenced JSON, brace scanning, and raw JSON.
- `evaluate_with_hermes.py:236-249`: `validate_result()` requires all keys in `EXPECTED_SCHEMA` and type/range checks.
- `db/evaluations.py:41-42`: stored decision defaults to `completed` in insert arguments.
- `db/evaluations.py:47-49`: job status uses `result.get("decision") == "completed"`; if decision is omitted, status becomes `skipped` despite stored default.
- `evaluate_with_hermes.py:330-355` and `evaluate_with_hermes.py:466-491`: DB evaluation path also updates intake JSON if external id file exists.
- `evaluate_with_hermes.py:397-415`: legacy intake file path writes status and fit report.

Known bug to include:
- Align omitted `decision` default in `db.evaluations.save_evaluation()`: compute decision once with default `completed` and use that for both the row and job status.

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| Evaluator tests | `python3 -m pytest tests/test_evaluator_parsing.py tests/test_evaluator_pack_prompt.py -q` | exit 0 |
| DB evaluation tests | `python3 -m pytest tests/test_evaluation_writeback.py -q` | exit 0 |
| Full tests | `python3 -m pytest -q` | exit 0 |
| Python syntax | `python3 -m py_compile evaluate_with_hermes.py db/evaluations.py` | exit 0 |

## Scope

In scope:
- `evaluate_with_hermes.py`
- `db/evaluations.py`
- New/extended tests under `tests/`

Out of scope:
- Removing intake JSON writeback entirely.
- Changing the evaluator prompt content, except if tests need stable fixtures.
- Calling real `hermes chat` in tests.
- Changing scoring rules.

## Git workflow

- Branch suggestion: `advisor/007-evaluator-characterization`

## Steps

### Step 1: Add tests for `extract_json()` shapes

Create `tests/test_evaluator_parsing.py` and cover:
- Raw JSON object.
- Fenced JSON with ```json.
- Hermes box wrapper format matching the regex in `extract_json()`.
- Text with invalid JSON before a later valid object, if current behavior supports it.
- Bad output returns `None`.

Do not call Hermes. Import and call `extract_json()` directly.

Verify: `python3 -m pytest tests/test_evaluator_parsing.py -q` → exit 0.

### Step 2: Add tests for `validate_result()` schema boundaries

In the same test file or another one, cover:
- Valid full schema returns empty issues.
- Missing required key reports a missing-key issue.
- Out-of-range score and level report issues.
- Wrong type reports issue.

Verify evaluator parsing tests again.

### Step 3: Fix and test omitted decision default in DB save

Add a DB test using temp SQLite:
- Insert a pending job.
- Call `save_evaluation(job_id, result)` with no `decision` key but otherwise valid fields.
- Assert evaluation row decision is `completed` and job status is `evaluated`, not `skipped`.

Then update `db/evaluations.py` so the same default value is used for both insert and status calculation.

Verify: `python3 -m pytest tests/test_evaluation_writeback.py -q` → exit 0.

### Step 4: Characterize intake writeback without live Hermes

Add tests around writeback helper behavior only if it can be done without a large refactor. If current code is too script-like, STOP after Step 3 and report that extracting a small writeback helper should be a separate plan. Do not perform a broad evaluator refactor in this plan.

## Test plan

- Parser tests are pure unit tests.
- DB save tests use temp DB monkeypatch like existing tests.
- No test should call real `hermes`, SSH, Archilles, or live intake directories.

## Done criteria

- [ ] `extract_json()` has direct tests for raw, fenced, Hermes-boxed, and invalid output.
- [ ] `validate_result()` has direct schema tests.
- [ ] Omitted decision defaults to evaluated/completed consistently.
- [ ] No tests call real Hermes.
- [ ] Focused tests pass.
- [ ] `python3 -m pytest -q` exits 0.
- [ ] Python syntax check exits 0.
- [ ] `plans/README.md` row 007 updated when done.

## STOP conditions

Stop and report if:
- Testing intake writeback requires large structural refactors.
- Importing `evaluate_with_hermes.py` tries to access live `/home/hermes` resources at import time.
- A parser behavior is clearly buggy but fixing it would change broad runtime behavior beyond characterization.

## Maintenance notes

These tests are a prerequisite for a future SQLite-source-of-truth cleanup. Reviewers should keep tests focused on observed behavior, not imagined ideal behavior.
