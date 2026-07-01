# Plan 036: Remove Archilles and Telegram from production code and config

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise.

> **Drift check (run first)**: `git diff --stat 481ac71..HEAD -- evaluate/cv_review.py packs_builder/job_pack.py api_server.py db/schema.py haxjobs.toml haxjobs_config.py server/routes/outreach.py server/routes/pack_resources.py db/role_classification.py`
> If any file changed significantly, compare excerpts against live code. Major mismatch → STOP.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: LOW
- **Depends on**: 035
- **Category**: tech-debt
- **Planned at**: commit `481ac71`, 2026-06-30

## Why this matters

"Archilles" is Arinze's personal VPS name. It's injected into employer-facing generated content — CV reviews, cover letters, and pack summaries. Employers reading "Archilles, 24/7 AI Agent Infrastructure" will have no idea what that means. Telegram delivery was the old notification model for that VPS. The new product is a web dashboard at `localhost:8241` — Telegram is dead weight in the codebase and config.

## Current state

### Archilles hits (14 locations)

**In generated employer-facing content (CRITICAL):**
- `evaluate/cv_review.py:270` — "cloud VPS (Archilles)" in generated CV skills list
```python
"skills": ["Python", ... "FastAPI", "PostgreSQL", "React", "Docker", "Linux", "cloud VPS (Archilles)"],
```
- `evaluate/cv_review.py:406` — "Runs on Archilles, a 24/7 AI agent VPS" in project descriptions
```python
"Runs on Archilles, a 24/7 AI agent VPS, with config-driven agent selection and automated cron scheduling.",
```
- `evaluate/cv_review.py:449,453` — project named "Archilles, 24/7 AI Agent Infrastructure"
```python
{"name": "Archilles, 24/7 AI Agent Infrastructure", "role": "Sole Developer", ...},
```
- `packs_builder/job_pack.py:203` — "I use Archilles daily" in cover letter copy
- `packs_builder/job_pack.py:206` — "Archilles and HaxJobs" in cover letter

**In code/docstrings (non-employer-facing):**
- `api_server.py:2` — docstring "Archilles Pipeline API"
- `db/schema.py:215` — comment about "older Archilles databases"
- `cv_variants/registry.json` — docstring about "live on Archilles"

**In config:**
- `haxjobs.toml:34` — `address = "archilleshaxsys@gmail.com"`

**In tests (4 hits):**
- `tests/test_cv_review.py` — assert "Archilles" in generated output
- `tests/test_*` — various assertions referencing Archilles

**NOT touching:**
- `profile/arinze_profile.local.json` — Archilles IS a legitimate project in Arinze's profile. Keep it there.

### Telegram hits (14 locations)

- `packs_builder/job_pack.py:24,59,348` — generates `telegram_summary.md` in every pack
- `server/routes/outreach.py:1` — docstring "Telegram integration"
- `server/routes/pack_resources.py:20` — lists `telegram_summary.md` as pack resource
- `db/role_classification.py:4,45` — "Telegram" as job source type
- `haxjobs.toml:37-39` — `[telegram]` config section
- `haxjobs_config.py:56-59` — `TELEGRAM_CHAT_ID`, `TELEGRAM_THREAD_ID`
- `tests/test_pack_detail_api.py:24` — creates `telegram_summary.md` fixture

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Run all tests | `PYTHONPATH=. python3 -m pytest -q tests/` | all pass |
| Compile check | `PYTHONPATH=. python3 -m py_compile evaluate/cv_review.py packs_builder/job_pack.py api_server.py haxjobs_config.py server/routes/outreach.py server/routes/pack_resources.py db/role_classification.py` | clean |
| Verify no Archilles in prod code | `grep -rn "archilles\|Archilles" --include="*.py" --include="*.sh" --include="*.toml" --include="*.json" . | grep -v ".git\|.claude\|state/\|packs/\|profile/\|tests/"` | only profile/ hits remain |
| Verify no Telegram in prod code | `grep -rn "telegram\|Telegram\|TELEGRAM" --include="*.py" --include="*.sh" --include="*.toml" . | grep -v ".git\|.claude\|state/\|packs/\|tests/"` | no hits |

## Scope

**In scope**:
- `evaluate/cv_review.py` — remove Archilles references, replace with generic terms
- `packs_builder/job_pack.py` — remove Archilles + telegram_summary
- `api_server.py` — fix docstring
- `db/schema.py` — remove comment
- `cv_variants/registry.json` — update docstring
- `haxjobs.toml` — rename email, remove [telegram]
- `haxjobs_config.py` — remove Telegram constants
- `server/routes/outreach.py` — fix docstring
- `server/routes/pack_resources.py` — remove telegram from pack resources
- `db/role_classification.py` — remove Telegram source type
- `tests/` — update assertions to not reference Archilles/Telegram

**Out of scope**:
- `profile/arinze_profile.local.json` — KEEP Archilles, it's user data
- Dashboard React code — separate plan
- Agent adapters — separate Wave 6B plan

## Git workflow

- Commit: `git commit -m "remove Archilles and Telegram from production code and config"`
- Do NOT push unless instructed

## Steps

### Step 1: Fix evaluate/cv_review.py — remove Archilles from generated CVs

Three changes:

**Line ~270 — skills list:** Replace `"cloud VPS (Archilles)"` with `"Linux server administration"` or just remove the Archilles reference from the string.

**Line ~406 — project description:** Replace `"Runs on Archilles, a 24/7 AI agent VPS"` with `"Runs on self-managed infrastructure"` or similar generic description.

**Lines ~449,453 — project entry:** Replace the project name `"Archilles, 24/7 AI Agent Infrastructure"` with `"24/7 AI Agent Infrastructure"` — drop the VPS name, keep the concept.

### Step 2: Fix packs_builder/job_pack.py — remove Archilles + telegram

**Archilles references:** Find and replace:
- `"I use Archilles daily"` → `"I use agent infrastructure daily"`
- `"through Archilles and HaxJobs"` → `"through agent infrastructure and HaxJobs"`

**Telegram:** Remove the `_render_telegram_summary` function entirely. Remove `"telegram_summary.md"` from the list of pack files. Remove the call that generates it.

### Step 3: Fix api_server.py docstring

Change `"""Archilles Pipeline API — serves live pipeline data as JSON for the dashboard."""` to `"""HaxJobs API — serves pipeline data as JSON for the dashboard."""`

### Step 4: Fix db/schema.py comment

Change `"Add reset-era job columns to older Archilles databases"` comment — remove "Archilles" reference or rewrite the comment entirely.

### Step 5: Fix cv_variants/registry.json docstring

Update any "live on Archilles" wording to generic terms.

### Step 6: Fix haxjobs.toml

**Email:** Change `address = "archilleshaxsys@gmail.com"` to something generic or use the user's configured email from the profile.

**Telegram:** Delete the entire `[telegram]` section (bot_token, chat_id, thread_id).

### Step 7: Fix haxjobs_config.py

Remove `TELEGRAM_CHAT_ID` and `TELEGRAM_THREAD_ID` constants. Remove the `[telegram]` section parsing.

### Step 8: Fix server/routes/outreach.py

Change docstring from "Telegram integration" to "Outreach integration".

### Step 9: Fix server/routes/pack_resources.py

Remove `"telegram_summary.md"` from the list of pack resources.

### Step 10: Fix db/role_classification.py

Remove "Telegram" as a job source type. Any references to Telegram as a source should be removed — jobs come from discovery scrapers and manual entry only.

### Step 11: Update tests

Fix test assertions that reference Archilles or telegram_summary. Key files:
- `tests/test_cv_review.py` — update expected project names
- `tests/test_pack_detail_api.py` — remove telegram_summary fixture
- Any other test with Archilles in assertions

### Step 12: Verify nothing remains

```bash
# Archilles in prod code (should return only profile/ hits)
grep -rn "archilles\|Archilles" --include="*.py" --include="*.sh" --include="*.toml" --include="*.json" . | grep -v ".git\|.claude\|state/\|packs/\|profile/\|tests/\|plans/\|docs/\|adapter_research/\|research/"

# Telegram in prod code (should return nothing)
grep -rn "telegram\|Telegram\|TELEGRAM" --include="*.py" --include="*.sh" --include="*.toml" . | grep -v ".git\|.claude\|state/\|packs/\|tests/\|plans/\|docs/\|adapter_research/\|research/"
```

### Step 13: Full test suite

**Verify**: `PYTHONPATH=. python3 -m pytest -q tests/` → all pass

### Step 14: Compile check

**Verify**: `PYTHONPATH=. python3 -m py_compile evaluate/cv_review.py packs_builder/job_pack.py api_server.py haxjobs_config.py server/routes/outreach.py server/routes/pack_resources.py db/role_classification.py` → clean

### Step 15: Commit

**Verify**: `git add -A && git commit -m "remove Archilles and Telegram from production code and config"` → exit 0

## Done criteria

- [ ] No "Archilles" in any production Python, shell, TOML, or JSON file (only profile/ remains)
- [ ] No "telegram" / "Telegram" / "TELEGRAM" in any production file
- [ ] `[telegram]` section removed from haxjobs.toml
- [ ] TELEGRAM_* constants removed from haxjobs_config.py
- [ ] `_render_telegram_summary` deleted
- [ ] Archilles references in generated CVs replaced with generic terms
- [ ] All tests pass

## STOP conditions

Stop and report back if:

- A test file outside the listed scope references Archilles or Telegram
- cv_review.py role-specific templates are more complex than expected — don't guess
- Removing telegram_summary breaks the pack builder in a way that cascades to other pack files

## Maintenance notes

The concept behind "Archilles" (24/7 agent infrastructure, self-managed VPS) is valid and valuable on a CV — but the name itself is meaningless to employers. Future CV generation should use profile-driven project names. If Arinze wants to keep "Archilles" as a project name, it should come from `profile/arinze_profile.local.json`, not be hardcoded in cv_review.py.
