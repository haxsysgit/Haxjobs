# Plan 037: Remove intake seeding and dead-architecture stragglers

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise.

> **Drift check (run first)**: `git diff --stat 481ac71..HEAD -- pipeline_db.py db/seed.py generate_ready_packs.py check_dashboard.py scripts/debug_job_pipeline.py`
> If any file changed, compare excerpts against live code. Major mismatch → STOP.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: 035, 036
- **Category**: tech-debt
- **Planned at**: commit `481ac71`, 2026-06-30

## Why this matters

After removing deprecated tables (035) and Archilles/Telegram (036), a few stragglers remain from the old architecture. `pipeline_db.py` still has `action_seed()` which reads from the gitignored `intake/` directory — a remnant of the JSON split-brain model. `db/seed.py` provides the `seed_from_intake()` function that backs it. These survived three cleanup waves because nobody traced the CLI dispatch end-to-end. Removing them completes the architecture cleanup.

## Current state

- `pipeline_db.py:17-21` — `action_seed()` imports from `db.seed` and reads `intake/`
```python
def action_seed():
    """Seed sample jobs from intake/ directory."""
    from db.seed import seed_from_intake
    n = seed_from_intake()
    print(f"Seeded {n} jobs from intake/")
```
- `db/seed.py` — `seed_from_intake()` function reads old JSON files from `intake/`
- `pipeline_db.py:248-249,270` — `seed` action in dispatch table + usage message
- `generate_ready_packs.py` — standalone pack generation script, may be superseded by evaluate/run.py auto-pack
- `check_dashboard.py` — dashboard health check, may be obsolete
- `scripts/debug_job_pipeline.py` — debug script, may reference old tables or patterns

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Run all tests | `PYTHONPATH=. python3 -m pytest -q tests/` | all pass |
| Compile pipeline_db | `PYTHONPATH=. python3 -m py_compile pipeline_db.py` | clean |
| Verify seed gone | `grep -c "action_seed\|seed_from_intake\|seed" pipeline_db.py` | 0 |
| Verify script runs | `PYTHONPATH=. python3 pipeline_db.py status` | exit 0, prints stats |

## Scope

**In scope**:
- `pipeline_db.py` — remove `action_seed()`, its import, and its dispatch entry
- `db/seed.py` — remove `seed_from_intake()` function (keep other seed functions if they exist)

**Out of scope**:
- `generate_ready_packs.py` — audit but don't delete. It may still be used for manual pack generation outside the pipeline.
- `check_dashboard.py` — keep. Useful for dev.
- `scripts/debug_job_pipeline.py` — keep. Debug tool.
- `intake/` directory — already gitignored, not tracked

## Git workflow

- Commit: `git commit -m "remove intake seeding and dead-architecture stragglers"`
- Do NOT push unless instructed

## Steps

### Step 1: Remove action_seed() from pipeline_db.py

Delete the entire `action_seed()` function. Remove the import of `seed_from_intake` if it was imported at the top. Remove `elif action == "seed":` entry from the dispatch table. Remove `seed|` from the usage message.

### Step 2: Remove seed_from_intake() from db/seed.py

Find `seed_from_intake()` in `db/seed.py` and delete the entire function. If this is the only function in the file, delete the file via `git rm`. If other seed functions remain, keep them.

### Step 3: Verify pipeline_db.py still works

**Verify**: `PYTHONPATH=. python3 pipeline_db.py status` → prints stats, exit 0

### Step 4: Compile check

**Verify**: `PYTHONPATH=. python3 -m py_compile pipeline_db.py db/seed.py` → clean

### Step 5: Full test suite

**Verify**: `PYTHONPATH=. python3 -m pytest -q tests/` → all pass

### Step 6: Commit

**Verify**: `git add -A && git commit -m "remove intake seeding and dead-architecture stragglers"` → exit 0

## Done criteria

- [ ] `action_seed()` removed from pipeline_db.py
- [ ] `seed_from_intake()` removed from db/seed.py (or file deleted if empty)
- [ ] `pipeline_db.py seed` no longer a valid command
- [ ] `pipeline_db.py status` still works
- [ ] All tests pass

## STOP conditions

Stop and report back if:

- Removing `seed_from_intake()` breaks other functions in `db/seed.py` — only remove the function, not shared utilities
- Any test imports `seed_from_intake` or calls `action_seed` — update the test first
- `generate_ready_packs.py` or `scripts/debug_job_pipeline.py` import from removed modules

## Maintenance notes

Test data seeding should move to discovery scrapers or a dedicated test fixture. The `intake/` directory was the old JSON split-brain model — jobs came from JSON files AND the database. Now all jobs come from scrapers → `discovered_jobs` → `jobs`. No seed path should read from `intake/` anymore.
