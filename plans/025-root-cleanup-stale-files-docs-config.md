# Plan 025: Root cleanup — delete stale files, fix docs, unify config

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat 004bd70..HEAD -- cv_generate.py cv_validator.py pack_builder.sh build-dash.sh dev-watch.sh .env.example docs/ scripts/READ*.md profile/role_taxonomy.json`
> If anything in this list was already deleted/modified, adjust scope accordingly.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: tech-debt + dx + docs
- **Planned at**: commit `004bd70`, 2026-06-29

## Why this matters

The repo root has 5 stale files from the pre-pipeline era. Docs claim plans are TODO that are DONE. `.env.example` documents zero actual env vars. `profile/role_taxonomy.json` is a 7.3KB ghost — 4 files still reference it even though `haxjobs.toml` is canonical. This is the polish pass: delete what's dead, update what's stale, so every file in the repo serves a purpose.

## Current state

**5 files to delete** (zero callers, zero imports):

| File | Evidence |
|------|----------|
| `cv_generate.py` (10KB) | Not imported, not called. Superseded by `packs_builder/job_pack.py`. Delete. |
| `cv_validator.py` (14KB) | Not imported, not called. References `cv_profile.typed.json` which doesn't exist. The *concept* (validating CV output against typed profile to prevent LLM hallucination) is important — captured as Plan 027. Delete the dead file. |
| `pack_builder.sh` (3.6KB) | Not called by cron or any script. Manual PDF export superseded by `_auto_pack()` in `evaluate/run.py`. Delete. |
| `build-dash.sh` (302B) | 3-line duplicate of `dashctl.sh deploy`. Zero callers. Delete. |
| `dev-watch.sh` (802B) | Orphaned. Vite dev server (`npm run dev`) handles HMR natively. Delete. |

**2 files to move to scripts/** (manual tools, not pipeline code)

None — `cv_validator.py` and `pack_builder.sh` have zero callers and reference files that don't exist.

**5 stale docs to update/delete:**

| File | Action |
|------|--------|
| `CV_FRAME_GOVERNANCE.md` (25KB) | Delete. Specifies abandoned architecture — references `cv_constants.py` (doesn't exist). The concept (typed CV validation to prevent LLM hallucination) is preserved and captured as Plan 027. |
| `docs/ROADMAP.md` | Update: mark waves 015-019 DONE, add 023-024, note Plan 010 rejected. |
| `docs/REPO_MAP.md` | Update: mark plans 015-022 DONE, add discovery scrapers tree. |
| `docs/BROWSER_EXTENSION.md` | Delete. Never built, no code exists. |
| `docs/ARCHITECTURE.md` | Keep but add a migration note: "As of Plan 017, classification is config-driven via `haxjobs.toml` `[[roles]]`. See `evaluation/role_family.py` for current code." |
| `skills/fit_evaluator.md` | Delete or archive. Superseded by `evaluate/common.py` + `evaluate/agents/hermes.py`. |

**`.env.example` needs rewrite:**

Current `.env.example` has 6 vars (all `EMAIL_*` + `GITHUB_TOKEN`). Actual `haxjobs_config.py` reads 15+:

```
HAXJOBS_HOME, HAXJOBS_DB, HAXJOBS_API_HOST, HAXJOBS_API_PORT,
HAXJOBS_API_TOKEN, HAXJOBS_PROFILE, HAXJOBS_CORS_ORIGINS,
HAXJOBS_MAX_POST_BODY, EMAIL_HOST, EMAIL_PORT, EMAIL_USER,
EMAIL_PASS, EMAIL_FROM, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
```

**`profile/role_taxonomy.json` ghost:**

Referenced by 4 files:
- `evaluation/role_family.py:load_role_profiles()` — fallback path when `haxjobs_config.ROLE_PROFILES` is empty. Keep the fallback but mark it `# ponytail: legacy fallback, remove when all test fixtures move to TOML`.
- `tests/test_role_family.py` — loads as test fixture
- `tests/test_application_templates.py` — loads as test fixture
- `tests/test_cv_variant_registry.py` — loads as test fixture

The 3 test files that load it: update them to use `haxjobs_config.ROLE_PROFILES` instead. If the tests need a specific taxonomy shape, construct it inline.

**`scripts/README.md`** references files that don't exist: `check_dashboard.py`, `cv_generate.py`, `cv_validator.py`. Rewrite to list actual scripts.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Run tests | `PYTHONPATH=. python3 -m pytest -q` | 217+ pass |
| Verify no references | `rg -l "<deleted-file>" --type py --type sh --type md` | zero results |
| Compile check | `PYTHONPATH=. python3 -m py_compile $(find . -path ./.git -prune -o -path ./dashboard -prune -o -name '*.py' -print)` | exit 0 |

## Scope

**In scope**:
- Delete: `cv_generate.py`, `cv_validator.py`, `pack_builder.sh`, `build-dash.sh`, `dev-watch.sh`
- Delete: `CV_FRAME_GOVERNANCE.md`, `docs/BROWSER_EXTENSION.md`, `skills/fit_evaluator.md`
- Update: `docs/ROADMAP.md`, `docs/REPO_MAP.md`, `docs/ARCHITECTURE.md`, `scripts/README.md`, `.env.example`
- Update: `evaluation/role_family.py` (add migration note on fallback)
- Update: 3 test files to stop loading `profile/role_taxonomy.json` as fixture
- Update: `plans/README.md` (add Plan 025 row)

**Out of scope**:
- Any changes to the pipeline logic (hooks, evaluation, classification)
- Dashboard code
- Adding new features
- Plan 026 (unified automation)

## Steps

### Step 1: Delete 5 orphaned root files

```bash
git rm cv_generate.py cv_validator.py pack_builder.sh build-dash.sh dev-watch.sh
```

**Verify**: `ls cv_generate.py cv_validator.py pack_builder.sh build-dash.sh dev-watch.sh` → all "No such file"

### Step 2: Delete 3 stale docs

```bash
git rm CV_FRAME_GOVERNANCE.md docs/BROWSER_EXTENSION.md skills/fit_evaluator.md
```

**Verify**: files gone

### Step 3: Update 4 stale docs

**`docs/ROADMAP.md`**: Find the section listing waves. Mark 015-019 DONE. Add: "Wave 3 — Modular Discovery (023-024) in progress. Plan 010 rejected (architecture mismatch)."

**`docs/REPO_MAP.md`**: Find the plans table. Mark 015-022 DONE. Add discovery tree:
```
discovery/
  normalize.py, hooks.py, __init__.py
  scrapers/
    greenhouse.py, __init__.py
```

**`docs/ARCHITECTURE.md`**: Add note at top of classification section: "As of Plan 017, role classification is config-driven via `haxjobs.toml` `[[roles]]`. See `evaluation/role_family.py:load_role_profiles()`."

**`scripts/README.md`**: Rewrite to list actual scripts: `archilles-webui`, `dash-tunnel`, `debug_job_pipeline.py`, `generate-pack`, `haxjobs-update`, `pull-cv-variants`, `render-cv-variant`, `review-pack`, `seed-cv-variants-from-packs`, `update-archilles-private`. One-line description each.

**Verify**: `git diff docs/ scripts/` shows only doc updates, no code changes.

### Step 4: Rewrite `.env.example`

Replace entire contents with all env vars from `haxjobs_config.py` `_env()` calls, organized by section. Format:

```bash
# HaxJobs environment variables
# Copy to .env and fill in values. All are optional (defaults in haxjobs_config.py).

# ── Core paths ──
# HAXJOBS_HOME=/home/hax/haxjobs-private-dev
# HAXJOBS_DB=state/haxjobs.db

# ── API server ──
# HAXJOBS_API_HOST=127.0.0.1
# HAXJOBS_API_PORT=8800
...
```

Include ALL vars found in `_env()` calls across the codebase. Don't guess — grep for them.

**Verify**: Each var in `.env.example` corresponds to a real `_env()` call. `rg "_env\(" haxjobs_config.py` and cross-check.

### Step 5: Remove role_taxonomy.json from test fixtures

**`evaluation/role_family.py`**: Add comment on the fallback block: `# ponytail: legacy fallback; remove when all test fixtures use TOML config`.

**3 test files**: `test_role_family.py`, `test_application_templates.py`, `test_cv_variant_registry.py` — find where they load `profile/role_taxonomy.json` and replace with inline test data or `haxjobs_config.ROLE_PROFILES`. The tests just need a role taxonomy to test against — they don't need the specific JSON file.

Then: `git rm profile/role_taxonomy.json`

**Verify**: `PYTHONPATH=. python3 -m pytest -q` — all 217 pass with zero `role_taxonomy.json` references in Python code. `rg role_taxonomy --type py` returns zero matches (except the comment in role_family.py).

### Step 6: Final verification

```bash
PYTHONPATH=. python3 -m pytest -q
PYTHONPATH=. python3 -m py_compile $(find . -path ./.git -prune -o -path ./dashboard -prune -o -name '*.py' -print)
```

**Verify**: All tests pass, compile clean, working tree clean.

## Test plan

No new tests needed. The existing 217 tests must continue to pass after removing `role_taxonomy.json` from fixtures.

## Done criteria

- [ ] 8 files deleted: `cv_generate.py`, `cv_validator.py`, `pack_builder.sh`, `build-dash.sh`, `dev-watch.sh`, `CV_FRAME_GOVERNANCE.md`, `docs/BROWSER_EXTENSION.md`, `skills/fit_evaluator.md`
- [ ] `profile/role_taxonomy.json` deleted
- [ ] 3 stale docs updated: `ROADMAP.md`, `REPO_MAP.md`, `ARCHITECTURE.md`
- [ ] `scripts/README.md` rewritten to match actual scripts
- [ ] `.env.example` covers all env vars from `haxjobs_config.py`
- [ ] `PYTHONPATH=. python3 -m pytest -q` — all 217 pass
- [ ] `rg "role_taxonomy" --type py` returns zero matches (except comment)
- [ ] `rg "cv_generate\|cv_validator\|pack_builder\|build-dash\|dev-watch" --type py --type sh` returns zero matches
- [ ] `plans/README.md` updated

## STOP conditions

- Any test fails after removing `role_taxonomy.json` from fixtures — the test fixture replacement must preserve the exact taxonomy shape the test needs.
- `rg -l <deleted-file>` returns matches in live code — that file is still referenced, don't delete it.
- A `.env.example` var doesn't match any `_env()` call — don't invent env vars.

## Maintenance notes

- `profile/role_taxonomy.json` was the canonical taxonomy before Plan 017. Now `haxjobs.toml` `[[roles]]` sections are canonical. The JSON file was a fallback for when TOML config is missing.
- `CV_FRAME_GOVERNANCE.md` described a CV generation system that was replaced by `packs_builder/job_pack.py` + `application_templates/`.
- `build-dash.sh` and `dev-watch.sh` were thin wrappers around npm commands. Vite handles both natively.
