# Plan 014: Remove intake JSON split-brain — DB is the only source of truth

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.

## Status

- **Priority**: P1
- **Effort**: M
- **Category**: tech-debt
- **Depends on**: none (independent of plan 010)
- **Planned at**: commit `451ea6a`, 2026-06-28
- **Drift check**: `git diff --stat 451ea6a..HEAD -- evaluate_with_hermes.py cron/sync_db_to_intake.py cron/email_intake.py cron/post_process.py post_process.py cron/run_pipeline.sh`
- **Note on dirty working tree**: Three files are modified from Stage 1 cleanup (haxjobs_config.py, cron/sync_db_to_intake.py, evaluate_with_hermes.py). The excerpts in "Current state" reflect the current HEAD (`451ea6a`). When executing, read the live file first — if patches fail due to Stage 1 changes, adapt the patch to the current file content.

## Why this matters

HaxJobs has two parallel data stores for the same information: `state/pipeline.db` (SQLite, the real source of truth) and `intake/*.json` (filesystem artifacts from the deleted discovery scrapers). The evaluator writes evaluation results to both. A cron sync script copies DB rows back to intake JSON. Several dead scripts still import and reference intake paths. The dashboard reads from the DB via the API — it never touches intake JSON. This split-brain creates confusion about which store is authoritative and wastes cycles on dual writes nobody reads.

After this plan: the DB is the undisputed source of truth. Evaluation results are written only to SQLite. Dead intake scripts are deleted. The intake directory and `db/seed.py` remain as a manual import utility — no automated pipeline touches intake anymore.

## Current state

### Files to delete (dead code — never called from pipeline, cron, or API)

- `cron/email_intake.py` — email intake pipeline. Not referenced by any cron script or `cron/run_pipeline.sh`. Searched: `grep -rn 'email_intake' cron/` returns no matches outside the file itself.
- `cron/post_process.py` — post-processing script. Not referenced by any cron script or pipeline. Searched: `grep -rn 'post_process' cron/run_pipeline.sh pipeline_db.py` returns no matches.
- `post_process.py` (repo root) — duplicate post-processing script. Same, never called.
- `cron/sync_db_to_intake.py` — syncs evaluations from DB to intake JSON files. The dashboard reads from DB via API, never touches intake. Searched: `grep -rn 'intake' dashboard/src/` returns zero matches. This sync has no consumer.

### File to clean: `evaluate_with_hermes.py` (HEAD `451ea6a`)

The evaluator has two code paths. The primary path (`evaluate_from_db()` on line 224, called by `--batch` and `--next`) reads from DB and saves to DB. But it also has intake-writeback code that mirrors evaluation results to intake JSON files. The secondary path (`evaluate_intake_file()` on line 358) reads from intake JSON, calls `evaluate_one_job()`, and writes back to both DB and intake. The fallback path (lines 501-511) runs when no pending DB jobs exist and tries intake files instead. The manual file-path argument (lines 532-535) routes to `evaluate_intake_file()`. The helper `get_pending_from_intake()` (line 428) scans intake JSON for pending files.

Code to remove from `evaluate_with_hermes.py`:

**`evaluate_from_db()` — remove intake writeback (lines 328-353):**
```python
# lines 328-353 in evaluate_from_db():
# Also update the intake JSON file if it exists
ext_id = job.get("external_id")
if ext_id:
    fpath = os.path.join(INTAKE_DIR, ext_id)
    if os.path.exists(fpath):
        try:
            intake = json.load(open(fpath))
            intake["status"] = "evaluated" ...
            intake["fit_report"] = {...
            with open(fpath, "w") as f:
                json.dump(intake, f, indent=2)
        except Exception as e:
            print(f"  WARNING: Could not update intake JSON: {e}")
```

**`--batch` path — remove intake writeback (lines 473-498):**
```python
# lines 473-498 in the --batch handler (lines 461-511):
# Also update the intake JSON file if it exists
ext_id = job.get("external_id")
if ext_id:
    fpath = os.path.join(INTAKE_DIR, ext_id)
    ...
```

**`--batch` path — remove intake fallback (lines 501-511):**
```python
# lines 501-511 in the --batch handler:
else:
    # Fall back to intake files
    files = get_pending_from_intake(limit)
    if not files:
        print("No pending jobs.")
        sys.exit(0)
    ok = 0
    for fpath in files:
        if evaluate_intake_file(fpath):
            ok += 1
    print(f"\nDone. {ok}/{len(files)} evaluated.")
```

Replace with:
```python
else:
    print("No pending jobs.")
    sys.exit(0)
```

**Delete `evaluate_intake_file()` (lines 358-425):** Entire function.

**Delete `get_pending_from_intake()` (lines 428-441):** Entire function.

**Remove manual file-path argument (lines 532-535):**
```python
# lines 532-535:
else:
    # Assume it's a file path
    ok = evaluate_intake_file(arg)
    sys.exit(0 if ok else 1)
```
Replace the `else:` block with an error message.

**Remove `INTAKE_DIR` from imports (line 16):**
Current:
```python
from haxjobs_config import HAXJOBS_HOME as BASE_DIR, INTAKE_DIR, PROFILE_PATH
```
Change to:
```python
from haxjobs_config import HAXJOBS_HOME as BASE_DIR, PROFILE_PATH
```

**Remove `INTAKE_DIR` usage in `evaluate_from_db()` (line 299):**
```python
# line 296-326 in evaluate_from_db():
result = evaluate_one_job(job)
if not result:
    ...
# Save to DB
result["evaluated_by"] = "hermes"
db.save_evaluation(job_id, result)
# (intake writeback removed — was lines 328-353)
return True
```

### File to clean: `cron/run_pipeline.sh`

Line 79 calls `sync_db_to_intake.py`:
```bash
python3 "$HAXJOBS_HOME/cron/sync_db_to_intake.py"
```
Remove this line. The classify-roles call on the previous line (78) stays.

### Files to keep (NOT in scope)

- `db/seed.py` — manual import utility (`pipeline_db.py seed`). Still useful for bootstrapping from intake JSON files.
- `pipeline_db.py` — `seed` CLI action. Keep.
- `haxjobs_config.py` and `haxjobs.toml` — `INTAKE_DIR` stays for seed.py.
- `intake/` directory — keep on disk for seed.py's import path.

### Repo conventions

- Python: stdlib-focused. Imports use `from haxjobs_config import X`. DB access via `db/*` modules.
- Bash: `set -euo pipefail`, functions lowercase, log with `tee -a "$LOG_FILE"`.
- Config: `haxjobs.toml` is canonical, `haxjobs_config.py` parses it with tomllib. Env vars override.
- Tests: pytest with monkeypatch for DB isolation. See `tests/test_manual_pack_generation.py` for the pattern.

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| Python compile | `python3 -m py_compile evaluate_with_hermes.py` | exit 0 |
| Bash syntax | `bash -n cron/run_pipeline.sh` | exit 0 |
| Run tests | `python3 -m pytest -q` | 218 passed (no regressions) |
| Pipeline smoke | `bash cron/run_pipeline.sh` | runs maintenance path, no errors |
| Verify no intake refs | `grep -c 'INTAKE_DIR' evaluate_with_hermes.py` | 0 |
| Verify dead files gone | `ls cron/email_intake.py cron/post_process.py post_process.py cron/sync_db_to_intake.py` | all "No such file" |
| Verify sync line gone | `grep -c 'sync_db_to_intake' cron/run_pipeline.sh` | 0 |

## Scope

**In scope:**

- `evaluate_with_hermes.py` — remove intake writeback, fallback, evaluate_intake_file(), get_pending_from_intake(), manual file-path argument, INTAKE_DIR import
- `cron/run_pipeline.sh` — remove sync_db_to_intake.py call
- DELETE: `cron/email_intake.py`
- DELETE: `cron/post_process.py`
- DELETE: `post_process.py`
- DELETE: `cron/sync_db_to_intake.py`

**Out of scope:**

- `db/seed.py` — manual utility, keep
- `pipeline_db.py` — keep seed CLI
- `haxjobs_config.py` — keep INTAKE_DIR
- `haxjobs.toml` — keep intake path
- `intake/` directory — keep on disk
- Any test files — the evaluator intake path is tested via mock; tests that mock internal functions (evaluate_intake_file, etc.) will break. Update them only if they import deleted functions directly.

## Steps

### Step 1: Delete dead intake scripts

Delete four files:
```bash
rm cron/email_intake.py
rm cron/post_process.py
rm post_process.py
rm cron/sync_db_to_intake.py
```

Verify: `ls cron/email_intake.py cron/post_process.py post_process.py cron/sync_db_to_intake.py 2>&1` → "No such file or directory" for all four.

### Step 2: Remove sync_db_to_intake call from cron/run_pipeline.sh

In `cron/run_pipeline.sh`, remove line 79:
```bash
python3 "$HAXJOBS_HOME/cron/sync_db_to_intake.py"
```

The line before it (78: `python3 pipeline_db.py classify-roles`) stays.

Verify: `bash -n cron/run_pipeline.sh` → exit 0. `grep -c 'sync_db_to_intake' cron/run_pipeline.sh` → 0.

### Step 3: Remove INTAKE_DIR import from evaluate_with_hermes.py

Line 16, change:
```python
from haxjobs_config import HAXJOBS_HOME as BASE_DIR, INTAKE_DIR, PROFILE_PATH
```
to:
```python
from haxjobs_config import HAXJOBS_HOME as BASE_DIR, PROFILE_PATH
```

Verify: `python3 -m py_compile evaluate_with_hermes.py` → exit 0 (may show import-not-used warnings, that's fine — verify no errors).

### Step 4: Remove intake writeback from evaluate_from_db()

In `evaluate_from_db()` (starts around line 224), remove lines 328-353 — the entire "Also update the intake JSON file" block.

The function should end with:
```python
result["evaluated_by"] = "hermes"
db.save_evaluation(job_id, result)
print(f"  → {result['fit_verdict']} (score={result['fit_score']}, level={result['level']})")
return True
```

Verify: `python3 -m py_compile evaluate_with_hermes.py` → exit 0.

### Step 5: Remove intake writeback from --batch path

In the `--batch` handler (around lines 461-511), remove lines 473-498 — the "Also update the intake JSON file" block inside the `for job in pending:` loop.

The loop should just do:
```python
for job in pending:
    result = evaluate_one_job(job)
    if result:
        result["evaluated_by"] = "hermes"
        db.save_evaluation(job["id"], result)
        print(f"  → {result['fit_verdict']} (score={result['fit_score']}, level={result['level']})")
    else:
        print(f"  FAILED for job #{job['id']}")
```

Verify: `python3 -m py_compile evaluate_with_hermes.py` → exit 0.

### Step 6: Remove intake fallback from --batch path

In the `--batch` handler, replace the `else:` block at lines 501-511 with a simple exit:

```python
    else:
        print("No pending jobs.")
        sys.exit(0)
```

Remove the entire intake fallback (lines 501-511):
```python
else:
    # Fall back to intake files
    files = get_pending_from_intake(limit)
    ...
```

Verify: `python3 -m py_compile evaluate_with_hermes.py` → exit 0.

### Step 7: Delete evaluate_intake_file() function

Delete the entire function at lines 358-425.

Verify: `python3 -m py_compile evaluate_with_hermes.py` → exit 0. `grep -c 'def evaluate_intake_file' evaluate_with_hermes.py` → 0.

### Step 8: Delete get_pending_from_intake() function

Delete the entire function at lines 428-441.

Verify: `python3 -m py_compile evaluate_with_hermes.py` → exit 0. `grep -c 'def get_pending_from_intake' evaluate_with_hermes.py` → 0.

### Step 9: Remove manual file-path argument

Replace the `else:` block at lines 532-535:
```python
    else:
        # Assume it's a file path
        ok = evaluate_intake_file(arg)
        sys.exit(0 if ok else 1)
```
with:
```python
    else:
        print(f"Unknown argument: {arg}")
        print("Usage:")
        print("  evaluate_with_hermes.py --next           # Next pending job from DB")
        print("  evaluate_with_hermes.py --batch 1        # Process 1 pending")
        print("  evaluate_with_hermes.py --all-pending    # Process all (one at a time)")
        sys.exit(1)
```

Verify: `python3 -m py_compile evaluate_with_hermes.py` → exit 0.

### Step 10: Verify zero INTAKE_DIR references remain in evaluator

Verify: `grep -c 'INTAKE_DIR' evaluate_with_hermes.py` → 0.

### Step 11: Run full test suite

```bash
python3 -m pytest -q
```

Expected: all tests pass. Some tests may fail if they import `evaluate_intake_file` or mock intake functions directly. If tests fail:

- `tests/test_intake_evaluation_flow.py` imports `evaluate_intake_file` — this test file tests the deleted function. Delete it: `rm tests/test_intake_evaluation_flow.py`.
- Run tests again after deleting any broken test files.

### Step 12: Run pipeline end-to-end

```bash
bash cron/run_pipeline.sh
```

Expected output: "No pending jobs. Running maintenance syncs only." → classify-roles runs → pipeline done. No errors. No reference to sync_db_to_intake.

## Test plan

- Existing tests should pass (delete `test_intake_evaluation_flow.py` if it fails)
- No new tests needed — this is deletion, not addition
- Pipeline smoke test confirms nothing broke

## Done criteria

- [ ] `ls cron/email_intake.py cron/post_process.py post_process.py cron/sync_db_to_intake.py` → all "No such file"
- [ ] `grep -c 'sync_db_to_intake' cron/run_pipeline.sh` → 0
- [ ] `grep -c 'INTAKE_DIR' evaluate_with_hermes.py` → 0
- [ ] `grep -c 'def evaluate_intake_file' evaluate_with_hermes.py` → 0
- [ ] `grep -c 'def get_pending_from_intake' evaluate_with_hermes.py` → 0
- [ ] `python3 -m py_compile evaluate_with_hermes.py` → exit 0
- [ ] `bash -n cron/run_pipeline.sh` → exit 0
- [ ] `python3 -m pytest -q` → all pass (minus deleted test file)
- [ ] `bash cron/run_pipeline.sh` → runs cleanly, no errors
- [ ] `plans/README.md` status row updated to DONE

## STOP conditions

Stop and report back (do not improvise) if:

- Patching `evaluate_with_hermes.py` fails because the code at the cited line numbers doesn't match (Stage 1 changes may have shifted lines). Re-read the file and adapt patch regions to the current content.
- Any step's verification fails after two reasonable fix attempts.
- Deleting `test_intake_evaluation_flow.py` doesn't fix the test suite — there may be other tests that import deleted functions. Investigate, report which tests fail, and wait for instructions.
- You discover other files importing `evaluate_intake_file` or `get_pending_from_intake` — report them, do not delete them without confirmation.

## Maintenance notes

- `db/seed.py` and `pipeline_db.py seed` remain as manual import tools. They read from `intake/` directory. If someone drops JSON files in `intake/`, `pipeline_db.py seed` will import them. This is intentional — the intake directory is a manual bootstrapping path, not an automated pipeline stage.
- If `evaluate_with_hermes.py` ever needs a writeback path again (e.g., to a new notification system), add it in `evaluate_from_db()` after the `db.save_evaluation()` call. Do not reintroduce filesystem JSON writes.
- `INTAKE_DIR` stays in `haxjobs.toml` and `haxjobs_config.py` for seed.py. Do not remove it without also removing seed.py.
