# Plan 023: Build Greenhouse scraper — modular discovery module template

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat b5c7a8b..HEAD -- discovery/ db/discovered_jobs.py`
> If any of these files changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: LOW
- **Depends on**: Plans 015, 016 (discovery spine + config contract — both DONE)
- **Category**: direction (feature)
- **Planned at**: commit `b5c7a8b`, 2026-06-29

## Why this matters

The discovery pipeline (Plans 015-016) has normalization, dedup, blacklist filtering, and promotion — but zero actual scrapers. Every job enters through `discover-manual`, which is a CLI, not a scraper. Greenhouse is the simplest ATS with a public JSON API, making it the ideal first scraper. This plan establishes the modular scraper pattern that Plan 024 will replicate for Ashby, Lever, and LinkedIn.

## Current state

The existing discovery infrastructure is ready to receive scraper output:

- `discovery/normalize.py` — `normalize_job(raw: dict, source: str) -> dict` maps scraper-specific fields to `CANONICAL_KEYS` (title, company, location, jd_text, source_url, apply_url, ats, external_id, source, raw_payload). Fields are auto-detected via `_first_of()` — it tries common field name variants.
- `discovery/hooks.py` — `should_accept_discovered_job(record) -> (bool, reason)` runs blacklist + non-tech filter from `[job_search]` config. Called by `pipeline_db.py discover-run`.
- `db/discovered_jobs.py` — `insert_discovered_job(record: dict) -> int | None` inserts into `discovered_jobs` table with dedup (source_url exact, then company+title case-insensitive). Returns row ID, or None on duplicate.
- `discovery/` directory exists at repo root with `__init__.py`, `normalize.py`, `hooks.py`. A `scrapers/` subpackage does NOT exist yet — this plan creates it.

Repo conventions to follow (from `AGENTS.md`):
- Python stdlib + SQLite, no ORM
- Imports: `from db.schema import get_db`, `from haxjobs_config import ...`
- Tests: `tmp_path + monkeypatch` pattern (see `tests/test_discovery_ingestion.py`)
- Verification: `PYTHONPATH=. python3 -m pytest -q`
- `ponytail:` comments mark deliberate simplifications

## Greenhouse API shape

Greenhouse hosts job boards at `https://boards.greenhouse.io/{company_name}`. The board returns a JSON API at `https://boards.greenhouse.io/embed/job_board?for={company_name}`. Some companies also have a consolidated API at `https://boards.greenhouse.io/{company_name}/jobs` which redirects or serves JSON.

**The canonical approach**: GET `https://boards.greenhouse.io/embed/job_board?for={company_name}` — returns JSON with a `jobs` array. Example response shape:

```json
{
  "jobs": [
    {
      "id": 1234567,
      "title": "Senior Software Engineer",
      "location": {"name": "London, UK"},
      "absolute_url": "https://boards.greenhouse.io/companyname/jobs/1234567",
      "departments": [{"name": "Engineering"}],
      "metadata": [{"name": "Employment Type", "value": "Full-time"}],
      "updated_at": "2026-06-28T12:00:00Z"
    }
  ],
  "meta": {"total_count": 42}
}
```

**To get the full JD text**, fetch the individual job page at the `absolute_url` and parse the HTML for the description section. The description lives in `<div id="content">` or `<div class="job__description">`.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Run tests | `PYTHONPATH=. python3 -m pytest -q tests/` | 207+ pass, exit 0 |
| Run scraper on one company | `PYTHONPATH=. python3 discovery/scrapers/greenhouse.py --company <name>` | prints job count, no errors |
| Check discovered jobs | `PYTHONPATH=. python3 -c "from db.schema import init, get_db; init(); c=get_db(); print(c.execute('SELECT COUNT(*) FROM discovered_jobs WHERE source=\\'greenhouse\\'').fetchone()[0]); c.close()"` | count > 0 |
| Compile check | `PYTHONPATH=. python3 -m py_compile discovery/scrapers/greenhouse.py` | exit 0 |

## Scope

**In scope** (files to create/modify):
- `discovery/scrapers/__init__.py` — new package init (empty or re-exports `scrape_greenhouse`)
- `discovery/scrapers/greenhouse.py` — the Greenhouse scraper module
- `tests/test_greenhouse_scraper.py` — new test file
- `pipeline_db.py` — add `scrape-greenhouse` CLI action
- `haxjobs.toml` — add `[discovery]` section with `greenhouse_companies` list (optional, for config-driven company lists)

**Out of scope** (do NOT touch):
- `discovery/normalize.py` or `discovery/hooks.py` — these are stable, scrapers consume them
- `db/discovered_jobs.py` — stable
- Any other scraper (Ashby, Lever, LinkedIn) — those are Plan 024
- Orchestrator that runs all scrapers — Plan 024

## Git workflow

- Commit per step or per logical unit
- Message style: `feat: add Greenhouse scraper module`
- Branch: `plans/023-greenhouse-scraper` (worktree or local branch)

## Steps

### Step 1: Create the scrapers package

Create `discovery/scrapers/__init__.py`:

```python
"""Modular scraper adapters for job discovery.

Each scraper module scrapes one source (Greenhouse, Ashby, Lever, etc.),
normalizes output through discovery.normalize.normalize_job(), and feeds
results into db.discovered_jobs.insert_discovered_job().

Scrapers are config-driven: company lists and settings live in haxjobs.toml
under [discovery].
"""
```

**Verify**: `PYTHONPATH=. python3 -c "import discovery.scrapers; print('OK')"` → prints OK

### Step 2: Write the Greenhouse scraper

Create `discovery/scrapers/greenhouse.py`. It must:

1. Accept a `--company` argument (or `--companies company1 company2 ...`)
2. For each company, fetch `https://boards.greenhouse.io/embed/job_board?for={company}`
3. Parse the JSON `jobs` array
4. For each job, fetch the full JD from `absolute_url` (parse HTML for description)
5. Call `normalize_job(raw, source="greenhouse")` with these field mappings:
   - `title` → job title
   - `company` → the company name being scraped (from the --company arg, NOT from the API response — Greenhouse responses don't include company name)
   - `location` → from `location.name`
   - `source_url` → `absolute_url`
   - `apply_url` → same as `absolute_url` (Greenhouse listings are also application pages)
   - `external_id` → the Greenhouse job `id` (integer)
   - `jd_text` → parsed HTML description from the individual job page
   - `ats` → `"greenhouse"`
6. Call `insert_discovered_job(normalized_record)`
7. Print summary: "Scraped {company}: {N} jobs found, {M} new"

Important implementation details:
- Use `urllib.request` + `json` from stdlib for the API call
- Use `re` module or `html.parser` (stdlib) for JD text extraction — look for content inside `<div id="content">` or `<div class="job__description">`
- Rate limit: 1 second between job detail page fetches (be polite)
- Handle HTTP errors gracefully — log and skip the job, don't crash
- Handle missing fields — use empty strings
- Add `__name__ == "__main__"` block with argparse for `--company` and `--companies`

**Verify**: Compile check passes: `PYTHONPATH=. python3 -m py_compile discovery/scrapers/greenhouse.py`

### Step 3: Scrape a real company

Run against a real Greenhouse-hosted company. Known Greenhouse-using companies (pick one):
- `datadog` — https://boards.greenhouse.io/datadog
- `cloudflare` — https://boards.greenhouse.io/cloudflare
- `stripe` — https://boards.greenhouse.io/stripe
- `spotify` — https://boards.greenhouse.io/spotify

```bash
PYTHONPATH=. python3 discovery/scrapers/greenhouse.py --company datadog
```

Check the output. You should see "Scraped datadog: N jobs found, M new".

**Verify**: 
```bash
PYTHONPATH=. python3 -c "
from db.schema import init, get_db
init()
c = get_db()
count = c.execute(\"SELECT COUNT(*) FROM discovered_jobs WHERE source='greenhouse'\").fetchone()[0]
print(f'Greenhouse jobs in discovered_jobs: {count}')
# Check at least one has jd_text populated
if count > 0:
    row = c.execute(\"SELECT title, company, jd_text FROM discovered_jobs WHERE source='greenhouse' LIMIT 1\").fetchone()
    has_jd = len(row[2]) > 100 if row[2] else False
    print(f'Sample: {row[1]} - {row[0]}, JD text populated: {has_jd}')
c.close()
"``` 
Expected: `count > 0`, `has_jd` is True.

### Step 4: Run through the pipeline

After scraping, run the discovery pipeline to promote accepted jobs:

```bash
PYTHONPATH=. python3 pipeline_db.py discover-run
```

**Verify**: 
```bash
PYTHONPATH=. python3 -c "
from db.schema import init, get_db
init()
c = get_db()
promoted = c.execute(\"SELECT COUNT(*) FROM discovered_jobs WHERE discovery_status='promoted' AND source='greenhouse'\").fetchone()[0]
rejected = c.execute(\"SELECT COUNT(*) FROM discovered_jobs WHERE discovery_status='rejected'\").fetchone()[0]
print(f'Promoted: {promoted}, Rejected: {rejected}')
c.close()
"```
Expected: Some jobs promoted (non-blacklisted companies), some possibly rejected if any match blacklist/filters.

### Step 5: Add scraper CLI to pipeline_db.py

Add a `scrape-greenhouse` action to `pipeline_db.py` that calls the greenhouse scraper. Follow the existing pattern for `discover-manual` (CLI action in the `if __name__ == "__main__"` block).

The new action should accept `--company <name>` and run the greenhouse scraper.

**Verify**: `PYTHONPATH=. python3 pipeline_db.py scrape-greenhouse --company datadog` works, produces output.

### Step 6: Write tests

Create `tests/test_greenhouse_scraper.py`. Since we can't hit the real API in tests, test:

1. `test_normalize_greenhouse_job` — Create a sample Greenhouse job dict (matching the real API shape) and verify `normalize_job()` maps it correctly. Assert that title, company, location, source_url, external_id, ats are all populated.

2. `test_greenhouse_jd_parsing` — Create a sample HTML snippet matching Greenhouse's job description format and verify the scraper's JD extraction function returns clean text (no HTML tags, reasonable length).

3. `test_insert_greenhouse_job` — Full integration: normalize a sample Greenhouse dict, call `insert_discovered_job()`, verify the row exists in the DB with correct fields.

Use the existing test conventions:
- `use_temp_db(monkeypatch, tmp_path)` pattern from `tests/conftest.py` (the shared `test_db` fixture)
- `from db import schema` for DB access
- `from discovery.normalize import normalize_job` for field mapping
- `from db.discovered_jobs import insert_discovered_job` for insertion

**Verify**: `PYTHONPATH=. python3 -m pytest -q tests/test_greenhouse_scraper.py` → all pass

### Step 7: Add config-driven company list (optional but recommended)

Add a `[discovery]` section to `haxjobs.toml`:

```toml
[discovery]
# Greenhouse companies to scrape (board slugs)
greenhouse_companies = [
    "datadog",
    "cloudflare",
]
```

Update `discovery/scrapers/greenhouse.py` to read from config when no `--company` is given:

```python
from haxjobs_config import load_config
config = load_config()
companies = config.get("discovery", {}).get("greenhouse_companies", [])
```

**Verify**: Running the scraper without `--company` scrapes the configured list.

## Test plan

All tests in `tests/test_greenhouse_scraper.py`:

- `test_normalize_greenhouse_job` — field mapping from API shape to CANONICAL_KEYS
- `test_greenhouse_jd_parsing` — HTML JD extraction returns clean text
- `test_insert_greenhouse_job` — full insert + DB verification

## Done criteria

- [ ] `PYTHONPATH=. python3 -m pytest -q` — all tests pass, including greenhouse tests
- [ ] `discovery/scrapers/__init__.py` exists and imports
- [ ] `discovery/scrapers/greenhouse.py` exists, compiles, and scrapes at least one real company
- [ ] `pipeline_db.py` has `scrape-greenhouse` CLI action
- [ ] At least 3 Greenhouse jobs exist in `discovered_jobs` with `source='greenhouse'` and populated JD text
- [ ] Jobs pass through `discover-run` and promote to main `jobs` table

## STOP conditions

Stop and report back (do not improvise) if:

- The Greenhouse API at `https://boards.greenhouse.io/embed/job_board?for={company}` returns a non-JSON response or 404/403 for all tested companies. The API format may have changed — we need to investigate before writing a scraper against it.
- HTTP requests to Greenhouse hang or timeout consistently (network issue, not a code bug).
- `normalize_job()` is called but doesn't map fields correctly (check that CANONICAL_KEYS are still the same set as in `discovery/normalize.py`).
- More than 2 test companies return 0 jobs — the API format might differ per company.

## Maintenance notes

- Greenhouse API format: if Greenhouse changes their board API, the JSON parsing in `greenhouse.py:fetch_jobs()` breaks. Test against a known-good company first to validate.
- Rate limiting: 1-second delay between job detail fetches. If scraping 100+ jobs per company, consider batching or caching.
- JD HTML extraction: Greenhouse occasionally updates their job page markup. The `<div id="content">` selector is the most stable but may need updating.
- Company name: scrapers provide the company name themselves (from the `--company` arg or config). Greenhouse API responses don't include company name — the scraper is responsible for setting it.
