# Plan 026: Unified automation — connect scrapers, CLI, and cron into one system

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat 004bd70..HEAD -- pipeline_db.py cron/run_pipeline.sh scripts/ haxjobs.toml`
> If Plan 024 scrapers aren't built yet, the `scrape-all` step is non-functional — skip that step and note it.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: LOW
- **Depends on**: Plan 024 (scrapers must exist), Plan 025 (clean root)
- **Category**: dx (tooling + automation)
- **Planned at**: commit `004bd70`, 2026-06-29

## Why this matters

Right now discovery (scraping + filtering + promotion) runs only when you type commands by hand. The cron pipeline skips it entirely: it goes straight to evaluation. The system can scrape 416 jobs from Greenhouse and filter to 4 relevant ones — but only if you remember to run `scrape-greenhouse` and `discover-run` yourself. The pipeline should be one command.

Additionally, there are 4 separate entry points for pipeline work (`pipeline_db.py`, `evaluate_with_hermes.py`, `cron/generate_cycle_report.py`, `generate_ready_packs.py`) with overlapping CLI styles. A single runner with subcommands makes the system feel cohesive.

## Current state

**The cron pipeline** (`cron/run_pipeline.sh`) does:
```
classify-roles → evaluate --batch 1 → classify-roles → generate_cycle_report
```

It skips:
```
✗ scrape-all       ← discovery never runs automatically
✗ discover-run     ← any manually-submitted discovered jobs sit idle
```

**Four separate entry points** doing pipeline work:
- `pipeline_db.py` — `seed`, `classify-roles`, `status`, `discover-manual`, `discover-run`, `scrape-greenhouse`
- `evaluate_with_hermes.py` — `--batch N`, `--all-pending`
- `cron/generate_cycle_report.py` — `--cycle-id`
- `generate_ready_packs.py` — standalone pack generation

**The `pipeline_db.py`** file is 139+ lines of monolithic `if __name__ == "__main__"` block with inline argparse for each action. It's the closest thing to a unified CLI but is awkward to extend.

**The cron schedule** processes 1 job per 30 minutes (48/day max). With 220+ pending jobs after a scraper run, that's 5 days to clear a backlog.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Run tests | `PYTHONPATH=. python3 -m pytest -q` | 217+ pass |
| Full pipeline | `PYTHONPATH=. python3 pipeline_db.py run-full` | prints stage-by-stage results |
| Scrape + discover | `PYTHONPATH=. python3 pipeline_db.py discover-full` | prints scraper + filter summary |
| Cron dry-run | `bash -n cron/run_pipeline.sh` | exit 0 |
| Compile check | `PYTHONPATH=. python3 -m py_compile pipeline_db.py` | exit 0 |

## Scope

**In scope**:
- `pipeline_db.py` — refactor into functions, add `run-full` and `discover-full` actions
- `cron/run_pipeline.sh` — wire discovery into the cron cycle
- `haxjobs.toml` — add optional `[cron]` section with batch sizes and schedule hints

**Out of scope**:
- Changing the evaluation logic
- Adding new scrapers (Plan 024)
- Dashboard changes
- API server changes

## Git workflow

- Commit as logical units (one for CLI refactor, one for cron wiring).
- Message style: match existing: `feat: unified pipeline CLI with discover-full and run-full`

## Steps

### Step 1: Refactor pipeline_db.py into functions

Current `pipeline_db.py` is a monolithic `if __name__ == "__main__"` block. Extract each action into a named function:

```python
def action_seed():
    """Seed sample jobs into the DB."""
    ...

def action_classify_roles():
    """Run role classification on pending jobs."""
    ...

def action_discover_manual(args):
    """Submit a job manually through discovery."""
    ...

def action_discover_run():
    """Process new discovered_jobs through hooks."""
    ...

def action_scrape_greenhouse(args):
    """Run the Greenhouse scraper."""
    ...

def action_discover_full():
    """Run ALL scrapers, then discover-run, then classify."""
    for scraper in [scrape_greenhouse, scrape_ashby, scrape_lever, scrape_linkedin]:
        scraper()  # each reads config for company lists
    action_discover_run()
    action_classify_roles()

def action_run_full():
    """Full pipeline: discover → classify → evaluate pending → report."""
    action_discover_full()
    # Evaluate all pending
    from evaluate.run import evaluate_from_db
    evaluate_from_db()  # processes all pending, auto-packs L1/L2
    # Generate report
    from cron.generate_cycle_report import main as report_main
    report_main([])
```

Each function prints its own summary. The `if __name__` block becomes:

```python
if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    actions = {
        "seed": action_seed,
        "classify-roles": action_classify_roles,
        "discover-manual": lambda: action_discover_manual(args),
        "discover-run": action_discover_run,
        "scrape-greenhouse": lambda: action_scrape_greenhouse(args),
        "discover-full": action_discover_full,
        "run-full": action_run_full,
        "status": action_status,
    }
    ...
```

**Verify**: 
```bash
PYTHONPATH=. python3 pipeline_db.py status          # existing action still works
PYTHONPATH=. python3 pipeline_db.py classify-roles  # existing action still works
PYTHONPATH=. python3 -m py_compile pipeline_db.py   # compiles
```

### Step 2: Add discover-full action

`discover-full` runs:
1. All configured scrapers (greenhouse, then future ashby/lever/linkedin)
2. `discover-run` (process new discovered_jobs through hooks → promote accepted)
3. `classify-roles` (assign role families)

**Verify**: 
```bash
PYTHONPATH=. python3 pipeline_db.py discover-full
```
Prints something like:
```
Greenhouse: datadog — 416 found, 328 new
...
Discover run: 4 accepted, 96 rejected
Classification: N classified, M unknown
```

### Step 3: Add run-full action

`run-full` runs the entire pipeline end-to-end:
1. `discover-full` (scrape → filter → promote → classify)
2. Evaluate all pending jobs
3. Generate cycle report

**Verify**: 
```bash
PYTHONPATH=. python3 pipeline_db.py run-full
```
Prints stage-by-stage progress. Completes without errors.

### Step 4: Wire discovery into cron

Update `cron/run_pipeline.sh` to run discovery before evaluation. Discovery shouldn't run every 30 minutes (too frequent). Two approaches:

**Option A: Conditional discovery (simplest)**
Run discovery once daily, evaluation every 30 min. Use a timestamp file:

```bash
DISCOVERY_MARKER="state/.last_discovery"
if [ ! -f "$DISCOVERY_MARKER" ] || [ $(find "$DISCOVERY_MARKER" -mmin +720) ]; then
    log "Running daily discovery cycle..."
    PYTHONPATH=. python3 pipeline_db.py discover-full 2>&1 | tee -a "$LOG_FILE"
    touch "$DISCOVERY_MARKER"
fi
```

**Option B: Separate cron entries**
Add a second cron entry that runs `discover-full` daily at 6am. Keep the 30-min evaluation cron as-is but add a pre-step that checks if discovery ran today.

Pick Option A — simpler, self-contained, no crontab editing needed.

**Verify**: 
```bash
bash -n cron/run_pipeline.sh           # syntax check
rm -f state/.last_discovery            # force discovery on next run
PYTHONPATH=. python3 pipeline_db.py discover-full 2>&1 | head -5  # still works standalone
```

### Step 5: Add configurable batch size

Add to `haxjobs.toml`:

```toml
[cron]
# How many jobs to evaluate per pipeline run
evaluate_batch = 1
# Discovery runs after N minutes since last run (720 = 12 hours)
discovery_interval_minutes = 720
```

Update `cron/run_pipeline.sh` to read from config:

```bash
BATCH=$(python3 -c "from haxjobs_config import load_config; c=load_config(); print(c.get('cron',{}).get('evaluate_batch',1))")
DISCOVERY_INTERVAL=$(python3 -c "from haxjobs_config import load_config; c=load_config(); print(c.get('cron',{}).get('discovery_interval_minutes',720))")
```

Use `$BATCH` instead of hardcoded `--batch 1`. Use `$DISCOVERY_INTERVAL` instead of `720`.

**Verify**: Change `evaluate_batch = 3` in `haxjobs.toml`, run cron script, verify it processes 3 jobs.

### Step 6: Delete build-dash.sh (if not already deleted in Plan 025)

`dashctl.sh deploy` already handles dashboard builds. `build-dash.sh` is a 3-line duplicate.

If Plan 025 didn't delete it, delete it here.

**Verify**: `ls build-dash.sh` → "No such file"

### Step 7: Final verification

```bash
# Full test suite
PYTHONPATH=. python3 -m pytest -q

# Compile check
PYTHONPATH=. python3 -m py_compile pipeline_db.py

# Cron syntax
bash -n cron/run_pipeline.sh

# Dry-run: discover-full should find scrapers or fail gracefully
PYTHONPATH=. python3 pipeline_db.py discover-full 2>&1 | head -10

# Dry-run: run-full (skip if no pending jobs — it may take a while)
PYTHONPATH=. python3 -c "
from pipeline_db import action_run_full
print('action_run_full is importable')
"
```

## Test plan

No new tests needed for CLI refactoring — existing tests cover the pipeline functions. The refactoring extracts code into functions without changing logic.

If the cron changes need testing, verify by:
1. `rm -f state/.last_discovery` — forces discovery on next cron run
2. `bash -x cron/run_pipeline.sh 2>&1 | grep "discovery"` — confirms discovery path is hit
3. `touch state/.last_discovery && bash -x cron/run_pipeline.sh 2>&1 | grep "discovery"` — confirms discovery is skipped when fresh

## Done criteria

- [ ] `pipeline_db.py` has named functions for each action (not monolithic `if __name__` block)
- [ ] `pipeline_db.py discover-full` runs scrapers → discover-run → classify-roles
- [ ] `pipeline_db.py run-full` runs full pipeline end-to-end
- [ ] `cron/run_pipeline.sh` includes discovery step (conditional on interval)
- [ ] `haxjobs.toml` has `[cron]` section with `evaluate_batch` and `discovery_interval_minutes`
- [ ] `PYTHONPATH=. python3 -m pytest -q` — all tests pass
- [ ] `bash -n cron/run_pipeline.sh` — syntax OK
- [ ] `build-dash.sh` is deleted (if Plan 025 didn't already)
- [ ] `plans/README.md` updated

## STOP conditions

- `discover-full` fails because no scrapers exist (Plan 024 not done) — skip scraper steps, just run `discover-run` + `classify-roles`. Note it.
- `run-full` hangs on evaluation — Hermes might be slow. Add a timeout or reduce batch size.
- Cron script changes break the existing flow — keep the original evaluation path intact, add discovery as a pre-step that fails gracefully.
- Any test that imports `pipeline_db` and relies on the old monolithic structure breaks — the refactoring should preserve the `if __name__` interface identically.

## Maintenance notes

- **Discovery frequency**: 12-hour intervals (720 minutes) is conservative. Tune `discovery_interval_minutes` in config. Too frequent and you hit rate limits; too infrequent and new jobs sit undiscovered.
- **Batch size**: 1 job per 30 min = 48/day. Increase `evaluate_batch` temporarily after a big scraper run to clear backlogs faster.
- **The `run-full` action** is for manual use. Don't wire it into cron — it would run ALL pending jobs and generate a report, which is slow. Cron should use the individual steps.
- **`pipeline_db.py`** will grow. If it exceeds ~300 lines, split into `pipeline_db.py` (DB operations) and `haxjobs_cli.py` (runner/orchestrator). Not needed yet.
