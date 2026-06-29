# Plan 024: Build remaining scrapers (Ashby, Lever, LinkedIn) + discovery orchestrator

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat b5c7a8b..HEAD -- discovery/ db/discovered_jobs.py pipeline_db.py haxjobs.toml`
> If Plan 023 is not DONE, STOP — this plan depends on the Greenhouse scraper pattern.
> If any discovery files changed in ways that conflict with the excerpts below, STOP.

## Status

- **Priority**: P1
- **Effort**: L
- **Risk**: MED (LinkedIn scraping is the riskiest — rate limits, auth, DOM changes)
- **Depends on**: Plan 023 (Greenhouse scraper — establishes the pattern)
- **Category**: direction (feature)
- **Planned at**: commit `b5c7a8b`, 2026-06-29

## Why this matters

Plan 023 established the modular scraper pattern: scrape → normalize → insert → discover-run. This plan replicates it for Ashby, Lever, and LinkedIn, then adds an orchestrator to run all scrapers in sequence. After this plan, discovery is fully automated — the pipeline goes from "manual CLI" to "run all scrapers → classify → evaluate → pack → report" without human intervention.

## Current state

The scraper framework from Plan 023 is in place:

- `discovery/scrapers/__init__.py` — package init
- `discovery/scrapers/greenhouse.py` — Greenhouse scraper (template/pattern)
- `discovery/normalize.py` — `normalize_job(raw, source)` maps to CANONICAL_KEYS
- `discovery/hooks.py` — `should_accept_discovered_job()` runs blacklist + non-tech filter
- `db/discovered_jobs.py` — `insert_discovered_job()` with dedup
- `pipeline_db.py` — has `discover-run`, `discover-manual`, and `scrape-greenhouse` CLI actions

Repo conventions (from `AGENTS.md`):
- Python stdlib + SQLite, no ORM
- `PYTHONPATH=. python3 -m pytest -q` for tests
- `tmp_path + monkeypatch` DB isolation pattern
- `ponytail:` comments for deliberate simplifications
- Config-driven via `haxjobs.toml` + `haxjobs_config.py`

## Suggested executor toolkit

- **Web access required**: The executor MUST be able to make HTTP requests to live job board APIs. Use curl, Python's `urllib`, or a headless browser as appropriate.
- Use `ponytail` skill for keeping scrapers minimal — stdlib HTTP + HTML parsing, no frameworks.
- **Reference**: Read `discovery/scrapers/greenhouse.py` before starting — each scraper follows the same pattern (see Plan 023 Steps 2-3 for the template).

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Run all tests | `PYTHONPATH=. python3 -m pytest -q tests/` | all pass |
| Run all scrapers | `PYTHONPATH=. python3 pipeline_db.py scrape-all` | prints per-scraper job counts |
| Run single scraper | `PYTHONPATH=. python3 discovery/scrapers/ashby.py --company <name>` | prints job count |
| Check discovered | `PYTHONPATH=. python3 -c "from db.schema import init, get_db; init(); c=get_db(); print(c.execute('SELECT source, COUNT(*) FROM discovered_jobs GROUP BY source').fetchall()); c.close()"` | counts per source |
| Compile check | `PYTHONPATH=. python3 -m py_compile discovery/scrapers/ashby.py discovery/scrapers/lever.py discovery/scrapers/linkedin.py` | exit 0 per file |

## Scope

**In scope** (files to create/modify):
- `discovery/scrapers/ashby.py` — Ashby ATS scraper
- `discovery/scrapers/lever.py` — Lever ATS scraper
- `discovery/scrapers/linkedin.py` — LinkedIn job search scraper
- `discovery/scrapers/orchestrator.py` — runs all scrapers in sequence
- `pipeline_db.py` — add `scrape-all`, `scrape-ashby`, `scrape-lever`, `scrape-linkedin` CLI actions
- `haxjobs.toml` — expand `[discovery]` section with company lists per scraper
- `tests/test_ashby_scraper.py` — Ashby scraper tests
- `tests/test_lever_scraper.py` — Lever scraper tests
- `tests/test_linkedin_scraper.py` — LinkedIn scraper tests
- `tests/test_orchestrator.py` — orchestrator tests
- `plans/README.md` — update status rows

**Out of scope** (do NOT touch):
- `discovery/normalize.py` — stable
- `discovery/hooks.py` — stable
- `db/discovered_jobs.py` — stable
- `evaluate/` — stable
- Greenhouse scraper — already done in Plan 023

---

## Step 1: Ashby scraper

### Ashby API shape

Ashby is an ATS that hosts job boards at `https://jobs.ashbyhq.com/{company}`. The public API endpoint is:

```
GET https://jobs.ashbyhq.com/api/non-user-graphql
```

It expects a GraphQL query. The listing query looks like:

```graphql
query {
  jobBoard {
    name
    jobPostings {
      id
      title
      locationNames
      url
      employmentType
      description { html }
      departmentName
      updatedAt
    }
  }
}
```

Or more commonly accessed via:
```
GET https://jobs.ashbyhq.com/{company}/api/jobs
```

Which returns a JSON array of job postings with keys: `id`, `title`, `location`, `url`, `descriptionHtml`, `department`, `employmentType`.

**Try the simpler endpoint first**: `GET https://jobs.ashbyhq.com/{company}/api/jobs`

### Field mapping (for normalize_job)

| Greenhouse field | CANONICAL_KEY |
|-----------------|---------------|
| `title` | title |
| Company name (from arg/config) | company |
| `location` or `locationNames[0]` | location |
| `descriptionHtml` or `description.html` | jd_text |
| `url` | source_url |
| `url` | apply_url |
| `id` (string/number) | external_id |
| `"ashby"` | ats |
| `"ashby"` | source |

### Implementation

Create `discovery/scrapers/ashby.py` following the exact same pattern as `greenhouse.py`:
1. Accept `--company` argument
2. Fetch `https://jobs.ashbyhq.com/{company}/api/jobs` (try this first; fall back to scraping the HTML page if JSON API returns 404)
3. For each job, JD text comes from `descriptionHtml` in the API response (NO separate page fetch needed — Ashby includes descriptions inline)
4. Call `normalize_job(raw, source="ashby")`
5. Call `insert_discovered_job(normalized_record)`

**Test companies** (known Ashby users): `anthropic`, `vercel`, `figma`, `notion`

**Verify**: Run against anthropic, check DB for Ashby jobs with populated JD text.

### Tests (in `tests/test_ashby_scraper.py`)

Same 3-test pattern as Greenhouse:
- `test_normalize_ashby_job` — field mapping from Ashby API shape
- `test_ashby_jd_cleanup` — verify HTML JD text is stripped cleanly
- `test_insert_ashby_job` — full insert + DB verification

---

## Step 2: Lever scraper

### Lever API shape

Lever hosts career pages at `https://jobs.lever.co/{company}`. The public API:

```
GET https://api.lever.co/v0/postings/{company}?mode=json
```

Returns a JSON array of postings. Each posting has:

```json
{
  "id": "abc123",
  "text": "Senior Engineer",
  "categories": {"location": "London", "team": "Engineering"},
  "hostedUrl": "https://jobs.lever.co/company/abc123",
  "applyUrl": "https://jobs.lever.co/company/abc123/apply",
  "descriptionPlain": "Full job description text here...",
  "description": "<html>Full JD...</html>",
  "createdAt": 1234567890000
}
```

### Field mapping

| Lever field | CANONICAL_KEY |
|------------|---------------|
| `text` | title |
| Company name (from arg/config) | company |
| `categories.location` | location |
| `descriptionPlain` | jd_text |
| `hostedUrl` | source_url |
| `applyUrl` | apply_url |
| `id` | external_id |
| `"lever"` | ats |
| `"lever"` | source |

**Key difference from Ashby**: Lever includes `descriptionPlain` (plain text) — this is the easiest JD text source. No HTML parsing needed.

### Implementation

Create `discovery/scrapers/lever.py`:
1. Accept `--company` argument
2. Fetch `https://api.lever.co/v0/postings/{company}?mode=json`
3. Use `descriptionPlain` for jd_text (no separate page fetch)
4. Call `normalize_job(raw, source="lever")`

**Test companies** (known Lever users): `github`, `netflix`, `shopify`, `spotify`

**Verify**: Run against github, check DB for Lever jobs.

### Tests (`tests/test_lever_scraper.py`)

Same pattern as Greenhouse/Ashby: normalize, JD cleanup, insert.

---

## Step 3: LinkedIn scraper

### LinkedIn approach

LinkedIn is the hardest to scrape. No public API for job listings. Options (in order of preference):

**Option A — Google dork + manual curation (safest)**
Use Google dork queries to find LinkedIn job listings, then extract structured data:
```
site:linkedin.com/jobs/view "software engineer" "london"
```
Parse the LinkedIn job page HTML for title, company, location, and description.

**Option B — Browser automation (most reliable, heavier)**
Use Playwright/Selenium to load LinkedIn job search pages. Navigate to search URLs like:
```
https://www.linkedin.com/jobs/search?keywords=python+backend&location=London
```
Extract job cards, then navigate to each detail page for full JD.

**Option C — LinkedIn API (if you have access)**
LinkedIn has a Jobs API but requires partner access.

**Start with Option A (simplest, no auth needed)**. If Google dork results don't include enough job detail, escalate to Option B.

### Field mapping

| LinkedIn page content | CANONICAL_KEY |
|----------------------|---------------|
| `<h1 class="job-title">` or `<title>` | title |
| `<span class="company-name">` or `<a class="company">` | company |
| `<span class="location">` | location |
| `<div class="description">` or `<div class="job-description">` | jd_text |
| Page URL | source_url |
| Page URL | apply_url |
| URL slug or data-id attribute | external_id |
| `"linkedin"` | ats |
| `"linkedin"` | source |

### Implementation notes

Create `discovery/scrapers/linkedin.py`:
- Implement the chosen approach (A, B, or C)
- If using Google dork: use `urllib` to search, parse results for LinkedIn job URLs, then fetch each URL and extract JD from HTML
- If using browser automation: launch a headless browser, load search page, extract job cards, navigate to each for full JD
- Call `normalize_job(raw, source="linkedin")`

**Rate limiting is critical**: LinkedIn aggressively rate-limits. Add 5-10 second delays between page fetches. Rotate user agents. Stop immediately if you get a 429 (rate limit) or CAPTCHA.

### STOP condition specific to LinkedIn

If after 3 attempts LinkedIn returns 429 or CAPTCHA for every request, STOP. Do not circumvent rate limits. Report back: "LinkedIn scraper blocked — needs authenticated API access or a different approach."

### Tests (`tests/test_linkedin_scraper.py`)

Test normalization and HTML parsing with sample LinkedIn page HTML. No live HTTP tests for LinkedIn — the rate limiting makes it impractical.

---

## Step 4: Config-driven company lists

Expand `haxjobs.toml` `[discovery]` section:

```toml
[discovery]
greenhouse_companies = ["datadog", "cloudflare"]
ashby_companies = ["anthropic", "vercel", "figma"]
lever_companies = ["github", "netflix"]
linkedin_search_queries = [
    "python backend engineer london",
    "fastapi developer remote uk",
]
```

Each scraper reads from its config section when no `--company` is specified.

---

## Step 5: Orchestrator

Create `discovery/scrapers/orchestrator.py`:

```python
"""Run all configured scrapers and process discovered jobs through the pipeline."""
from discovery.scrapers.greenhouse import scrape_greenhouse
from discovery.scrapers.ashby import scrape_ashby
from discovery.scrapers.lever import scrape_lever
from discovery.scrapers.linkedin import scrape_linkedin

def run_all_scrapers():
    """Run every configured scraper, then promote accepted jobs."""
    results = {}
    results["greenhouse"] = scrape_greenhouse()
    results["ashby"] = scrape_ashby()
    results["lever"] = scrape_lever()
    results["linkedin"] = scrape_linkedin()
    # Then run discover-run to promote
    ...
```

Each scraper module has a `scrape_*` function that reads from config, returns `{"new": N, "duplicates": M, "errors": E}`.

---

## Step 6: CLI wiring

Add to `pipeline_db.py`:
- `scrape-ashby --company <name>` → runs Ashby scraper
- `scrape-lever --company <name>` → runs Lever scraper
- `scrape-linkedin --query "<search>"` → runs LinkedIn scraper
- `scrape-all` → runs orchestrator (all scrapers + discover-run)
- `discover-full` → shortcut: scrape-all → classify-roles (future: → evaluate)

**Verify**: `PYTHONPATH=. python3 pipeline_db.py scrape-all` runs all scrapers.

---

## Step 7: Wire into cron

Update `cron/run_pipeline.sh` to include scraper step before evaluation:

```bash
# Run all discovery scrapers
PYTHONPATH=. python3 pipeline_db.py scrape-all 2>&1 | tee -a "$LOG_FILE"
```

But be careful: running all scrapers every 30 minutes is excessive. Initially, add it behind a separate schedule or a flag. The cron script already processes 1 job per run — discovery should run less frequently (e.g., once daily).

---

## Test plan

| File | Tests | What they verify |
|------|-------|-----------------|
| `test_ashby_scraper.py` | 3 | normalize, JD cleanup, insert |
| `test_lever_scraper.py` | 3 | normalize, JD cleanup, insert |
| `test_linkedin_scraper.py` | 2 | normalize, HTML parsing (no live HTTP) |
| `test_orchestrator.py` | 2 | run_all calls all scrapers, errors don't crash |

All follow the same pattern as `test_greenhouse_scraper.py` and use the shared `test_db` fixture from `tests/conftest.py`.

---

## Done criteria

- [ ] `PYTHONPATH=. python3 -m pytest -q` — all tests pass
- [ ] `discovery/scrapers/ashby.py` exists, compiles, scrapes at least one real company
- [ ] `discovery/scrapers/lever.py` exists, compiles, scrapes at least one real company
- [ ] `discovery/scrapers/linkedin.py` exists, compiles (live scrape optional — if rate-limited, HTML parsing test is sufficient)
- [ ] `discovery/scrapers/orchestrator.py` exists and `scrape-all` runs
- [ ] `haxjobs.toml` has `[discovery]` with company lists for each scraper
- [ ] `pipeline_db.py` has `scrape-all` and per-scraper CLI actions
- [ ] `plans/README.md` status rows updated

## STOP conditions

- **Ashby**: All 3 test companies return non-JSON or empty responses → API format may have changed.
- **Lever**: `api.lever.co/v0/postings/{company}?mode=json` returns errors for all companies → API may be deprecated.
- **LinkedIn**: Rate-limited (429) or CAPTCHA on 3 consecutive attempts → cannot scrape, needs different approach.
- Any scraper crashes with an unhandled exception on 2 different test companies → bug in the scraper, not the API.

## Maintenance notes

- **LinkedIn is the riskiest scraper.** Their job page HTML changes frequently, and they aggressively block scrapers. Be prepared to switch approaches (Google dork → browser automation → API) as needed.
- **Rate limits**: All scrapers should have configurable delays. LinkedIn needs 5-10s, others can be 1-2s.
- **Company lists in config**: Keep them small (5-10 companies per scraper) to avoid excessive load. Add new companies as needed.
- **Orchestrator failure handling**: If one scraper fails, others should still run. The orchestrator must catch exceptions per-scraper and report which ones succeeded/failed.
- **Discovery schedule**: Running all scrapers too frequently hits rate limits and wastes resources. Recommend daily or twice-daily scrape schedule separate from the 30-minute evaluation pipeline.
