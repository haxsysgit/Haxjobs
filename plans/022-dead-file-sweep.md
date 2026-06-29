# Plan 022: Delete remaining dead scripts and orphaned files

> Executor: deletion-only. Do not refactor or rewrite anything.
>
> Drift check: not applicable.

## Status

- Priority: P2
- Effort: S
- Risk: LOW
- Depends on: none
- Category: tech-debt
- Planned at: commit `451ea6a`, 2026-06-28

## Why this matters

Stages 1-2 deleted discovery/ and intake scripts. Ten more standalone scripts have zero external references — nothing in the pipeline, cron, API, or dashboard calls them. They're dead weight that confuses anyone reading the repo.

## Current state

Root scripts with zero external refs:
- `check_dashboard.py` — dashboard integrity checker, 122 lines. Not called by cron/pipeline/API.
- `cv_generate.py` — CV generation orchestrator, 279 lines. Not called by cron/pipeline/API.
- `cv_profile_helper.py` — CV profile helper. Not called.
- `cv_validator.py` — CV validator, 328 lines. Not called.
- `dev_reload.py` — dev reload utility. Not called.

Cron scripts with zero external refs:
- `cron/draft_outreach.py` — outreach drafting. Not called from run_pipeline.sh or any cron script.
- `cron/import_linkedin_jobs.py` — LinkedIn import. Dead (discovery/ deleted).
- `cron/review_outreach.py` — outreach review. Not called.
- `cron/send_email.py` — email sending. Not called.
- `cron/weekly_report.py` — weekly report. Not called (cycle report will replace this in plan 019).

## Decision per file

Delete (7 files — clearly dead, zero refs, no manual use case):
- `cron/import_linkedin_jobs.py` — LinkedIn scraper deleted
- `cron/draft_outreach.py` — not wired to pipeline
- `cron/review_outreach.py` — not wired
- `cron/send_email.py` — not wired
- `cron/weekly_report.py` — will be replaced by plan 019
- `cv_profile_helper.py` — not called
- `dev_reload.py` — not called

Keep (3 files — standalone utilities that might be manually useful):
- `check_dashboard.py` — dashboard checker, useful for debugging
- `cv_generate.py` — CV generation, might be used standalone
- `cv_validator.py` — CV validation, might be used standalone

## Steps

### Step 1: Delete dead cron scripts

```bash
rm cron/import_linkedin_jobs.py
rm cron/draft_outreach.py
rm cron/review_outreach.py
rm cron/send_email.py
rm cron/weekly_report.py
```

### Step 2: Delete dead root scripts

```bash
rm cv_profile_helper.py
rm dev_reload.py
```

### Step 3: Verify

- `ls cron/import_linkedin_jobs.py` → No such file
- `grep -r 'import_linkedin_jobs\|draft_outreach\|review_outreach\|send_email\|weekly_report' cron/ run_pipeline.sh 2>/dev/null` → zero matches
- `python3 -m pytest -q` → remaining tests pass

### Step 4: Record kept scripts

In `scripts/README.md` (create if absent):
```
# Standalone utility scripts

These are not called by the pipeline. They're manual tools.

- check_dashboard.py — verify dashboard index.html references real files
- cv_generate.py — CV-FRAME pipeline orchestrator (fill templates from profile)
- cv_validator.py — CV-FRAME validator (assertions before PDF export)
```

## Done criteria

- 7 dead files deleted
- No pipeline, cron, or test references to deleted files remain
- `scripts/README.md` documents the 3 kept utilities
- `python3 -m pytest -q` passes

## Stop conditions

Stop if any file marked for deletion is imported by remaining code. Re-check references before deleting.
