# Plan 003: Fix LinkedIn cache import flow

> **Executor instructions**: Follow this plan step by step. Run every verification command and confirm expected results. If a STOP condition occurs, stop and report.
>
> **Drift check (run first)**: `git diff --stat b725a33..HEAD -- discovery/linkedin_local_scraper.py cron/import_linkedin_jobs.py tests`

## Status

- **Priority**: P1
- **Effort**: S/M
- **Risk**: MED
- **Depends on**: plans/001-restore-verification-baseline.md
- **Category**: correctness / security
- **Planned at**: commit `b725a33`, 2026-06-27

## Why this matters

LinkedIn blocks VPS IPs, so the intended architecture is local scrape on Jade, cache results, copy to Archilles, then import over SSH. The current local scraper still contains a direct HTTP POST path to `http://178.105.245.120:8800/api/queue`, and the importer discards real company names by writing `company="LinkedIn"`. This breaks source-first discovery and pushes the system toward an unsafe public API dependency.

## Current state

Relevant files:
- `discovery/linkedin_local_scraper.py` — local Playwright scraper and optional sender.
- `cron/import_linkedin_jobs.py` — Archilles-side cache importer.
- `db/jobs.py` — `insert_job()` API.
- Tests: no importer tests currently found.

Current excerpts:
- `discovery/linkedin_local_scraper.py:20-21`: `ARCHILLES_API = "http://178.105.245.120:8800/api/queue"`.
- `discovery/linkedin_local_scraper.py:47-65`: `send_to_archilles(job)` POSTs directly to that API.
- `discovery/linkedin_local_scraper.py:198-205`: `--send` loops through jobs and calls direct API send.
- `discovery/linkedin_local_scraper.py:211-214`: scraper writes `/tmp/linkedin_jobs_cache.json` already.
- `cron/import_linkedin_jobs.py:30-36`: importer inserts `company="LinkedIn"` and uses title/url only.

Product constraint:
- The HaxJobs skill states the correct pattern is `python3 discovery/linkedin_local_scraper.py`, `scp /tmp/linkedin_jobs_cache.json archilles:/tmp/`, then `ssh archilles python3 cron/import_linkedin_jobs.py /tmp/linkedin_jobs_cache.json`. Do not route local HTTP requests to Archilles API.

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| Importer tests | `python3 -m pytest tests/test_linkedin_import.py -q` | exit 0 |
| Full tests | `python3 -m pytest -q` | exit 0 |
| Python syntax | `python3 -m py_compile $(find . -path './dashboard/node_modules' -prune -o -path './.git' -prune -o -path './.venv' -prune -o -name '*.py' -print)` | exit 0 |

## Scope

In scope:
- `discovery/linkedin_local_scraper.py`
- `cron/import_linkedin_jobs.py`
- New tests under `tests/`
- README/docs only if command usage changes

Out of scope:
- Changing LinkedIn selectors or scraping cadence.
- Adding auto-connect or auto-message behavior.
- Reading or committing `discovery/linkedin_cookies.json`.
- Making the Archilles API public.

## Git workflow

- Branch suggestion: `advisor/003-linkedin-cache-import-flow`
- Keep changes small: importer test/fix, then local scraper command behavior.

## Steps

### Step 1: Preserve company names during cache import

In `cron/import_linkedin_jobs.py`, use `job.get("company") or "Unknown"` for the company field. Keep `source="linkedin_local"`. Preserve title, location, URL, and jd_text behavior.

Add tests using a temporary JSON cache and monkeypatched/temp DB similar to other DB tests. The test should import a job with `company="ExampleCo"` and assert the DB row stores `ExampleCo`, not `LinkedIn`.

Verify: `python3 -m pytest tests/test_linkedin_import.py -q` → exit 0.

### Step 2: Remove or disable direct public HTTP POST sending

Remove `ARCHILLES_API` and `send_to_archilles()` from `discovery/linkedin_local_scraper.py`, or leave a stub that raises a clear error saying direct API send is no longer supported. Replace `--send` behavior with an explicit cache workflow message, or rename to `--upload` only if you implement safe `scp` + `ssh archilles python3 cron/import_linkedin_jobs.py /tmp/linkedin_jobs_cache.json`.

Preferred minimal behavior:
- Default run scrapes and writes `/tmp/linkedin_jobs_cache.json`.
- If `--send` is passed, print the two exact commands to run or perform the `scp` + `ssh import` sequence using `subprocess.run([...])` lists, not shell strings.
- Do not POST to `178.105.245.120:8800`.

Verify: search `discovery/linkedin_local_scraper.py` for `178.105.245.120` and `ARCHILLES_API`; no direct API URL remains.

### Step 3: Document the safe workflow where the script usage appears

Update the script docstring and any relevant README/docs to say local scrape writes cache, then SCP/SSH import. Keep it short.

Verify: `python3 -m py_compile discovery/linkedin_local_scraper.py cron/import_linkedin_jobs.py` → exit 0.

## Test plan

- New importer regression: cached company is preserved.
- New malformed-cache/fallback test if cheap: missing company becomes `Unknown` without crashing.
- Existing full pytest suite.

## Done criteria

- [ ] LinkedIn cache import preserves scraped company names.
- [ ] No direct HTTP POST to Archilles public IP remains in `linkedin_local_scraper.py`.
- [ ] Safe cache + SCP/SSH workflow is documented in script usage.
- [ ] Focused importer tests pass.
- [ ] `python3 -m pytest -q` exits 0.
- [ ] Python compile command exits 0.
- [ ] No LinkedIn cookie files are read or committed.
- [ ] `plans/README.md` row 003 updated when done.

## STOP conditions

Stop and report if:
- The operator explicitly wants to keep direct HTTP API sending.
- The import path requires live SSH to Archilles during unit tests.
- Cache file shape differs from `linkedin_local_scraper.py` output and cannot be inferred safely.

## Maintenance notes

Future scrapers for VPS-blocked sites should follow this same pattern: local cache artifact, transfer, structured import. Do not reintroduce direct calls to the live API.
