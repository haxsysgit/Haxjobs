# Plan 015: Restore discovery-first ingestion with dedup and filters

> Executor: implement this plan only. Do not work on classification, evaluation agents, packs, or reports yet.
>
> Drift check: `git diff --stat 451ea6a..HEAD -- haxjobs.toml haxjobs_config.py db/schema.py db/jobs.py pipeline_db.py cron/run_pipeline.sh tests/`

## Status

- Priority: P1
- Effort: L
- Risk: MED
- Depends on: none
- Category: architecture / correctness
- Planned at: commit `451ea6a`, 2026-06-28

## Why this matters

The product definition is discovery-first. Jobs should mostly enter HaxJobs from scraping/discovery, with manual paste/link entry as a fallback that goes through the same pipeline. The current repo has no discovery stage after cleanup. Jobs only enter through manual queue/import paths. That makes the pipeline backwards: it evaluates what humans feed it instead of producing a daily discovered job universe.

## Current state

- `discovery/` was deleted during cleanup because the old scrapers were dead and not wired.
- `cron/run_pipeline.sh` currently starts from existing DB rows and runs classification/evaluation.
- `db/schema.py` has a `jobs` table with fields like `external_id`, `title`, `company`, `jd_text`, `source_url`, `source`, `status`, `role_family`, `pack_status`.
- There is no raw scraped job table, no blacklist check, no duplicate check before insert beyond `external_id UNIQUE`, and no discovery artifact model.

## Target design

Add a boring discovery ingestion layer:

1. Scrapers/manual submit normalize job records into one shape.
2. Pre-discovery hooks run before insert:
   - duplicate URL/company/title check against DB
   - blacklist companies from config
   - optional exact/near duplicate role check
3. Raw discovered jobs are stored in DB, not scattered JSON files.
4. Post-discovery hooks mark obvious non-tech or profile-irrelevant jobs as filtered, but leniently.
5. Accepted jobs become candidates for classification.

## Scope

In scope:
- `db/schema.py`
- new `db/discovered_jobs.py`
- new `discovery/` package with tiny stdlib modules only
- `pipeline_db.py` CLI additions
- `cron/run_pipeline.sh`
- tests for dedup, blacklist, manual submit same path

Out of scope:
- Real browser automation or LinkedIn scraping
- Agent evaluation
- Pack generation
- Messaging/email report
- 3-agent simulation loop

## Implementation steps

### Step 1: Add DB storage for discovered/raw jobs

Add `discovered_jobs` table in `db/schema.py`:
- `id`
- `source` (`manual`, `greenhouse`, `ashby`, `lever`, etc.)
- `source_url`
- `apply_url`
- `ats`
- `external_id`
- `title`
- `company`
- `location`
- `jd_text`
- `raw_payload_json`
- `discovery_status` (`new`, `duplicate`, `blacklisted`, `filtered`, `accepted`, `promoted`)
- `filter_reason`
- `created_at`, `updated_at`

Add indexes on `source_url`, `company`, `title`, `discovery_status`.

Verify: `python3 - <<'PY'
from db import schema
schema.init()
conn=schema.get_db()
print([r[1] for r in conn.execute('PRAGMA table_info(discovered_jobs)')])
PY` includes the table columns.

### Step 2: Add `db/discovered_jobs.py`

Implement:
- `insert_discovered_job(record: dict) -> int | None`
- `find_duplicate(record: dict) -> dict | None`
- `list_discovered_jobs(status: str | None = None, limit: int = 100)`
- `promote_discovered_job(discovered_id: int) -> int`

Use stdlib SQLite through `db.schema.get_db()`. Keep it simple. No ORM.

Verify: small temp DB test inserts one discovered job, duplicate insert returns/marks duplicate, promotion creates a row in `jobs`.

### Step 3: Add minimal discovery normalization

Create `discovery/normalize.py`:
- `normalize_job(raw: dict, source: str) -> dict`
- Ensure keys exist: title, company, location, jd_text, source_url, apply_url, ats, external_id, source.
- Use `source_url` as fallback external id.

No scraping implementation yet. This plan creates the spine, not every scraper.

### Step 4: Add pre/post hooks

Create `discovery/hooks.py`:
- `is_blacklisted_company(company, config) -> bool`
- `is_obvious_non_tech(title, jd_text) -> bool`
- `should_accept_discovered_job(record, config) -> tuple[bool, str]`

Use config values from plan 016 if already implemented. If plan 016 is not done, add temporary empty defaults in the hook module and mark a TODO to switch to config. Do not hardcode Arinze-specific role families here.

### Step 5: Add manual entry through same path

Manual queue/API should call discovery normalization and hooks before promotion. If changing API is too large, add a CLI first:

`python3 pipeline_db.py discover-manual --title ... --company ... --url ... --jd-file ...`

It should insert into `discovered_jobs`, run hooks, and promote to `jobs` only if accepted.

### Step 6: Wire cron lightly

In `cron/run_pipeline.sh`, add a discovery placeholder call before classify/evaluate:

`python3 pipeline_db.py discover-run`

`discover-run` can initially process already-present discovered jobs and promote accepted ones. Do not add real scraping yet.

## Tests to write or rewrite

Create `tests/test_discovery_ingestion.py`:
- duplicate source_url does not create a second accepted job
- blacklisted company gets `discovery_status='blacklisted'`
- obvious non-tech role gets `filtered`
- manual job and scraped job use same normalization path
- accepted discovered job promotes into `jobs`

## Done criteria

- `discovered_jobs` table exists with indexes.
- `pipeline_db.py discover-manual` works on a temp DB.
- Duplicate jobs are rejected before promotion.
- Blacklisted companies are rejected before promotion.
- Accepted raw jobs promote to `jobs` exactly once.
- `python3 -m pytest -q tests/test_discovery_ingestion.py` passes.
- Existing suite still passes or stale tests are rewritten to match this design.

## Stop conditions

Stop if implementing real scrapers becomes necessary. This plan is only the ingestion spine.
