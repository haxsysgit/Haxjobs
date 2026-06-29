# Plan 012: Fix evaluate_intake_file — evaluation saved to wrong job ID

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.

> **Drift check (run first)**: `git diff --stat 451ea6a..HEAD -- evaluate_with_hermes.py`
> If this file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: bug
- **Planned at**: commit `451ea6a`, 2026-06-28
- **Issue**: (none)

## Why this matters

The legacy intake-file evaluation path (`evaluate_intake_file` in `evaluate_with_hermes.py`) has a bug where after Hermes evaluates a job, the result is saved to a DIFFERENT job than the one that was evaluated. The function calls `db.get_pending_jobs(1)` to find "the" job to write to — but this grabs whatever job is alphabetically first by `discovered_at`, not the job that was just evaluated. If multiple jobs are pending, the evaluation score and verdict get attached to the wrong row in the database.

This path is triggered when someone runs `python3 evaluate_with_hermes.py intake/somefile.json` or when the batch path falls back to intake files. The primary DB path (`evaluate_from_db`) is NOT affected — it correctly saves to the evaluated job's ID. But the intake-file path is a loaded footgun.

## Current state

- `evaluate_with_hermes.py` — `evaluate_intake_file` function at lines 358–416. The bug is at lines 390–393.
- `tests/test_evaluator_parsing.py` — tests `extract_json` and `validate_result` only. No tests for the evaluation flow itself.

The buggy code (`evaluate_with_hermes.py:370-393`):
```python
    # Ensure job exists in DB
    fname = os.path.basename(fpath)
    db_job = db.get_job(db.insert_job(
        title=job.get("title", "Unknown"),
        company=job.get("company", "Unknown"),
        location=job.get("location", ""),
        jd_text=job.get("jd_text", ""),
        source_url=job.get("source_url", ""),
        source=job.get("source", "unknown"),
        external_id=fname,
    ))

    if not db_job:
        print(f"  WARNING: Could not sync to DB, evaluating from file only")

    result = evaluate_one_job(job)
    if not result:
        return False

    # Save to DB if possible
    db_jobs = db.get_pending_jobs(1)       # <-- BUG: grabs ANY pending job
    if db_jobs:
        result["evaluated_by"] = "hermes"
        db.save_evaluation(db_jobs[0]["id"], result)  # <-- saves to wrong job
```

The problem chain:
1. `db.insert_job(...)` returns a job ID (new row) or `None` (duplicate by `external_id`)
2. `db.get_job(None)` silently returns `None` (no error, but `db_job` is `None`)
3. The code prints a warning but continues
4. After evaluation, `db.get_pending_jobs(1)` returns the FIRST pending job by `discovered_at` — which may be an entirely different job
5. The evaluation result is saved using that wrong job ID

The fix: capture the job ID from step 1 and use it directly. If `insert_job` returns `None` on duplicate, query the existing job by `external_id`.

For comparison, the correct pattern in `evaluate_from_db` (line 307–326):
```python
def evaluate_from_db():
    db.init()
    pending = db.get_pending_jobs(1)
    if not pending:
        return False
    job = pending[0]
    job_id = job["id"]
    # ...
    result = evaluate_one_job(job)
    # ...
    db.save_evaluation(job_id, result)  # <-- correct: uses the evaluated job's ID
```

Repo conventions: functions return `bool` for success/failure. Log with `print()` to stdout. Use `db.*` module functions through the `pipeline_db` compat import.

## Commands you will need

| Purpose   | Command                  | Expected on success |
|-----------|--------------------------|---------------------|
| Tests     | `python3 -m pytest -q`   | 209+ passed         |
| Bash syntax | `bash -n cron/run_pipeline.sh scripts/haxjobs-update dashctl.sh build-dash.sh dev-watch.sh pack_builder.sh` | exit 0 |
| Python compile | `python3 -m py_compile evaluate_with_hermes.py` | exit 0 |

## Scope

**In scope** (the only files you should modify):
- `evaluate_with_hermes.py` — fix `evaluate_intake_file` (lines 370–393)

**Out of scope** (do NOT touch):
- `evaluate_from_db` function — it's correct, don't change it
- `evaluate_one_job` — correct, don't change it
- `db/jobs.py`, `db/evaluations.py` — the DB layer is correct
- Any other file

## Git workflow

- Branch: `fix/012-intake-eval-wrong-job` off `main`
- Commit message: `fix: evaluate_intake_file saves evaluation to the correct job ID`
- Do NOT push or open a PR unless instructed.

## Steps

### Step 1: Add a characterization test

Create `tests/test_intake_evaluation_flow.py` with a test that verifies the fix. The test should:

1. Create a temp directory with a fake intake JSON file
2. Monkeypatch `INTAKE_DIR`, `BASE_DIR`, and `PROFILE_PATH` to point to temp paths
3. Create a minimal profile JSON
4. Call `evaluate_intake_file(fpath)` — it will attempt a real Hermes call
5. Instead of calling real Hermes, monkeypatch `evaluate_one_job` to return a canned result for the job being tested
6. Verify that `db.save_evaluation` was called with the correct job ID (the one that was just inserted for this intake file)

Since the function calls Hermes (which is slow/expensive), this test should mock `evaluate_one_job`. The test file should look like:

```python
"""Test that evaluate_intake_file saves to the correct job ID."""
import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import evaluate_with_hermes as ev
from db.schema import init as init_db, get_db


def test_evaluate_intake_file_saves_to_correct_job(tmp_path, monkeypatch):
    """The evaluation must be saved against the job inserted from the intake file."""
    # Setup temp dirs
    intake_dir = tmp_path / "intake"
    intake_dir.mkdir()
    state_dir = tmp_path / "state"
    state_dir.mkdir()

    # Create intake file
    intake_file = intake_dir / "test_job_001.json"
    intake_file.write_text(json.dumps({
        "title": "Python Dev",
        "company": "TestCo",
        "location": "London",
        "jd_text": "Write code",
        "source_url": "https://example.com",
        "source": "test",
        "status": "pending",
    }))

    # Create minimal profile
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(json.dumps({
        "user_profile": {"name": "Test User", "email": "test@test.com"},
        "confirmed_profile_facts": [],
        "evaluation_context": {},
        "company_notes": {},
    }))

    # Redirect config paths
    monkeypatch.setattr(ev, "INTAKE_DIR", str(intake_dir))
    monkeypatch.setattr(ev, "BASE_DIR", str(tmp_path))
    monkeypatch.setattr(ev, "PROFILE_PATH", str(profile_path))

    # Redirect DB to temp
    db_path = tmp_path / "test.db"
    monkeypatch.setattr("haxjobs_config.DB_PATH", str(db_path))
    # Force re-import of haxjobs_config in db.schema
    import importlib
    import haxjobs_config
    importlib.reload(haxjobs_config)

    init_db()

    # Mock evaluate_one_job to return a predictable result
    fake_result = {
        "fit_score": 75,
        "fit_verdict": "GOOD_FIT",
        "level": 2,
        "level_name": "Quick Apply",
        "strongest_matches": ["Python experience"],
        "major_gaps": [],
        "sponsorship_risk": "low",
        "summary": "Good match",
        "decision": "completed",
        "skip_reason": "",
        "role_type": "backend",
        "evaluated_by": "hermes",
    }
    monkeypatch.setattr(ev, "evaluate_one_job", lambda job: fake_result)

    # Run
    result = ev.evaluate_intake_file(str(intake_file))
    assert result is True

    # Verify: the evaluation was saved to the correct job (by external_id)
    conn = get_db()
    job_row = conn.execute(
        "SELECT id FROM jobs WHERE external_id = ?", ("test_job_001.json",)
    ).fetchone()
    assert job_row is not None, "Job should exist in DB with external_id"
    job_id = job_row["id"]

    eval_row = conn.execute(
        "SELECT fit_score FROM evaluations WHERE job_id = ?", (job_id,)
    ).fetchone()
    assert eval_row is not None, f"Evaluation should exist for job {job_id}"
    assert eval_row["fit_score"] == 75
    conn.close()
```

**Verify**: `python3 -m pytest tests/test_intake_evaluation_flow.py -q -x` → the test FAILS (confirming the bug exists)

### Step 2: Fix evaluate_intake_file

Open `evaluate_with_hermes.py`. Replace lines 370–393 (from `# Ensure job exists in DB` through the save-to-DB block) with:

```python
    # Ensure job exists in DB — track the job_id explicitly
    fname = os.path.basename(fpath)
    new_job_id = db.insert_job(
        title=job.get("title", "Unknown"),
        company=job.get("company", "Unknown"),
        location=job.get("location", ""),
        jd_text=job.get("jd_text", ""),
        source_url=job.get("source_url", ""),
        source=job.get("source", "unknown"),
        external_id=fname,
    )

    # Resolve the DB job ID — insert_job returns None on duplicate, so look it up
    eval_job_id = new_job_id
    if eval_job_id is None:
        conn = db.schema.get_db()
        row = conn.execute(
            "SELECT id FROM jobs WHERE external_id = ?", (fname,)
        ).fetchone()
        conn.close()
        eval_job_id = row["id"] if row else None

    if eval_job_id is None:
        print(f"  WARNING: Could not sync to DB, evaluating from file only")

    result = evaluate_one_job(job)
    if not result:
        return False

    # Save to DB using the resolved job ID
    if eval_job_id is not None:
        result["evaluated_by"] = "hermes"
        db.save_evaluation(eval_job_id, result)
```

**Verify**: `python3 -m pytest tests/test_intake_evaluation_flow.py -q -x` → the test PASSES

### Step 3: Run full verification baseline

**Verify**:
- `python3 -m pytest -q` → 210+ tests pass (209 existing + 1 new)
- `python3 -m py_compile evaluate_with_hermes.py` → exit 0

## Test plan

One new test in `tests/test_intake_evaluation_flow.py`:
- `test_evaluate_intake_file_saves_to_correct_job` — verifies the evaluation is written against the correct job ID

## Done criteria

ALL must hold:

- [ ] `python3 -m pytest -q` exits 0, 210+ tests pass
- [ ] The `evaluate_intake_file` function no longer contains `db.get_pending_jobs` call
- [ ] No files outside `evaluate_with_hermes.py` and `tests/test_intake_evaluation_flow.py` modified
- [ ] `python3 -m py_compile evaluate_with_hermes.py` exits 0

## STOP conditions

Stop and report back (do not improvise) if:
- The code at `evaluate_with_hermes.py:390` doesn't contain `db_jobs = db.get_pending_jobs(1)` as shown in "Current state"
- The new test file has import errors that aren't fixable by adding standard library imports
- The `db.schema` module doesn't expose `get_db` (it does — confirmed)

## Maintenance notes

- The `evaluate_intake_file` function is marked as legacy ("Legacy path — prefer DB path"). If intake JSON support is eventually removed entirely, this function can be deleted. Until then, the fix ensures it doesn't corrupt data.
- The dual-write pattern (SQLite + intake JSON) is a known architectural debt item. This fix only addresses the ID mismatch bug, not the broader dual-write concern.
- The `db.insert_job` function uses `external_id` for deduplication (returns `None` on duplicate), which is why the fix queries by `external_id` when `insert_job` returns `None`.
