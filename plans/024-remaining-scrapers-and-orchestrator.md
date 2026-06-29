# Plan 024: Build Ashby + Lever scrapers and discovery orchestrator

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
- **Effort**: M
- **Risk**: MED
- **Depends on**: Plan 023 (Greenhouse scraper — establishes the pattern)
- **Category**: direction (feature)
- **Planned at**: commit `b5c7a8b`, 2026-06-29

## Why this matters

Plan 023 established the modular scraper pattern: scrape → normalize → insert → discover-run. This plan replicates it for Ashby and Lever, then adds an orchestrator to run public ATS scrapers in sequence.

The goal is not to mass-ingest huge career boards. Discovery should stay profile-aware: small or interesting companies first, then title/location filtering before insertion.

## Current state

The scraper framework from Plan 023 is in place:

- `discovery/scrapers/__init__.py` — package init
- `discovery/scrapers/greenhouse.py` — Greenhouse scraper (template/pattern)
- `discovery/normalize.py` — `normalize_job(raw, source)` maps to CANONICAL_KEYS
- `discovery/hooks.py` — `should_accept_discovered_job()` runs blacklist + non-tech filter
- `db/discovered_jobs.py` — `insert_discovered_job()` with dedup
- `pipeline_db.py` — has `discover-run`, `discover-manual`, and `scrape-greenhouse` CLI actions

Repo conventions:

- Python stdlib + SQLite, no ORM
- `PYTHONPATH=. python3 -m pytest -q` for tests
- `tmp_path + monkeypatch` DB isolation pattern
- `ponytail:` comments for deliberate simplifications
- Config-driven via `haxjobs.toml` + `haxjobs_config.py`

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Run all tests | `PYTHONPATH=. python3 -m pytest -q tests/` | all pass |
| Run all scrapers | `PYTHONPATH=. python3 pipeline_db.py scrape-all` | prints per-scraper job counts |
| Run Ashby | `PYTHONPATH=. python3 discovery/scrapers/ashby.py --company <name>` | prints found/matched/new counts |
| Run Lever | `PYTHONPATH=. python3 discovery/scrapers/lever.py --company <name>` | prints found/matched/new counts |
| Compile check | `PYTHONPATH=. python3 -m py_compile discovery/scrapers/ashby.py discovery/scrapers/lever.py discovery/scrapers/orchestrator.py` | exit 0 per file |

## Scope

**In scope**:

- `discovery/profile_search.py` — shared profile-aware title/location filtering
- `discovery/scrapers/ashby.py` — Ashby ATS scraper
- `discovery/scrapers/lever.py` — Lever ATS scraper
- `discovery/scrapers/orchestrator.py` — runs public ATS scrapers in sequence
- `pipeline_db.py` — add `scrape-all`, `scrape-ashby`, and `scrape-lever` CLI actions
- `haxjobs.toml` — company lists and profile search terms
- `tests/test_profile_search.py` — profile filter tests
- `tests/test_ashby_scraper.py` — Ashby scraper tests
- `tests/test_lever_scraper.py` — Lever scraper tests
- `tests/test_orchestrator.py` — orchestrator tests
- `plans/README.md` — update status rows

**Out of scope**:

- `discovery/normalize.py` — stable
- `discovery/hooks.py` — stable
- `db/discovered_jobs.py` — stable
- `evaluate/` — stable
- Greenhouse scraper core route — already done in Plan 023

---

## Step 1: Ashby scraper

Ashby hosts job boards at `https://jobs.ashbyhq.com/{company}`.

The stale simple endpoint may 404:

```text
https://jobs.ashbyhq.com/{company}/api/jobs
```

Use Ashby's public non-user GraphQL endpoint instead:

```text
POST https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobBoardWithTeams
POST https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobPosting
```

Implementation:

1. Accept `--company`, `--companies`, and optional `--query` arguments.
2. Fetch job summaries with `ApiJobBoardWithTeams`.
3. Filter by profile search terms before fetching detail JDs.
4. Fetch full `descriptionHtml` for matched jobs with `ApiJobPosting`.
5. Strip HTML into readable JD text.
6. Call `normalize_job(raw, source="ashby")`.
7. Call `insert_discovered_job(normalized_record)`.

Suggested smaller/nicer Ashby boards:

- `posthog`
- `incident`
- `paddle`
- `sequence`
- `faculty`

Tests:

- normalize mapping
- JD cleanup
- profile filtering
- insert + DB verification

---

## Step 2: Lever scraper

Lever hosts career pages at `https://jobs.lever.co/{company}`.

Public API:

```text
GET https://api.lever.co/v0/postings/{company}?mode=json
```

Implementation:

1. Accept `--company`, `--companies`, and optional `--query` arguments.
2. Fetch the company postings JSON.
3. Filter by profile search terms before insertion.
4. Use `descriptionPlain` for JD text.
5. Fall back to stripped `description` HTML when plain text is missing.
6. Call `normalize_job(raw, source="lever")`.
7. Call `insert_discovered_job(normalized_record)`.

Suggested smaller/nicer Lever board:

- `zopa`

Tests:

- normalize mapping
- plain-text JD preference
- profile filtering
- insert + DB verification

---

## Step 3: Profile-aware search filtering

Discovery must search according to Arinze's profile, not dump every role from every board.

Add shared filtering in `discovery/profile_search.py`:

- read profile search terms from `haxjobs.toml` `[discovery].profile_search_terms`
- fall back to configured role titles if search terms are absent
- reject excluded levels and blacklisted keywords from `[job_search]`
- reject extra discovery exclusions such as sales/account/customer-success roles
- keep unknown locations, but prefer London, UK, Remote UK, EMEA, or Europe

Each scraper should:

1. Fetch the board.
2. Filter job summaries by title/location.
3. Fetch or parse full JD only for matched jobs.
4. Insert only matched jobs.
5. Print `found`, `matched`, and `new` counts.

---

## Step 4: Config-driven company lists

Expand `haxjobs.toml` `[discovery]` with small, profile-aligned public ATS boards:

```toml
[discovery]
greenhouse_companies = ["monzo"]
ashby_companies = ["posthog", "incident", "paddle", "sequence", "faculty"]
lever_companies = ["zopa"]
profile_search_terms = ["backend", "software engineer", "python", "ai engineer", "platform engineer"]
profile_excluded_terms = ["account", "sales", "customer success", "recruiter"]
```

Keep these lists small. Add new boards only after a live probe proves they have relevant roles.

---

## Step 5: Orchestrator

Create `discovery/scrapers/orchestrator.py`:

- runs Greenhouse, Ashby, and Lever in sequence
- catches errors per scraper so one source cannot kill the whole run
- prints compact source-level summaries including `found`, `matched`, `new`, and `errors`

---

## Step 6: CLI wiring

Add to `pipeline_db.py`:

- `scrape-ashby --company <name>` → runs Ashby scraper
- `scrape-lever --company <name>` → runs Lever scraper
- `scrape-all` → runs orchestrator

Verify:

```bash
PYTHONPATH=. python3 pipeline_db.py scrape-all
```

---

## Step 7: Cron note

Do not wire public ATS scraping into the 30-minute evaluation loop by default.

Discovery should run less frequently, likely daily or twice daily. Keep cron wiring separate until the private pipeline has a confirmed schedule.

---

## Test plan

| File | Tests | What they verify |
|------|-------|-----------------|
| `test_profile_search.py` | 3 | target title kept; unrelated/excluded titles rejected |
| `test_ashby_scraper.py` | 4 | normalize, JD cleanup, profile filter, insert |
| `test_lever_scraper.py` | 4 | normalize, JD cleanup, profile filter, insert |
| `test_orchestrator.py` | 2 | run_all calls all scrapers, errors don't crash |

All scraper tests use sample payloads and the shared `test_db` fixture. Live HTTP checks belong in manual verification, not pytest.

---

## Done criteria

- [ ] `PYTHONPATH=. python3 -m pytest -q` — all tests pass
- [ ] `discovery/profile_search.py` exists and filters irrelevant titles before insert
- [ ] `discovery/scrapers/ashby.py` exists, compiles, and scrapes at least one real company
- [ ] `discovery/scrapers/lever.py` exists, compiles, and scrapes at least one real company
- [ ] `discovery/scrapers/orchestrator.py` exists and `scrape-all` runs
- [ ] `haxjobs.toml` has small company lists and profile search terms
- [ ] `pipeline_db.py` has `scrape-all`, `scrape-ashby`, and `scrape-lever`
- [ ] `plans/README.md` status rows updated

## STOP conditions

- **Ashby**: all probed companies return non-JSON or empty responses → API format may have changed.
- **Lever**: `api.lever.co/v0/postings/{company}?mode=json` returns errors for all probed companies → API may be deprecated.
- Any scraper crashes with an unhandled exception on 2 different test companies → bug in the scraper, not the API.

## Maintenance notes

- Prefer small public ATS boards over giant enterprise boards.
- Keep source lists grounded in live probes.
- Do not add boards just because a company is famous.
- If a board has many jobs, filter by title/location before fetching expensive detail pages or inserting rows.
- Running all scrapers too frequently hits rate limits and wastes local/runtime resources.
