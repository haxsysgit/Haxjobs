# Plan 016: Expand haxjobs.toml into the user/profile/job-search contract

> Executor: implement config only. Do not rewrite classifier/evaluator logic in this plan.
>
> Drift check: `git diff --stat 451ea6a..HEAD -- haxjobs.toml haxjobs_config.py tests/`

## Status

- Priority: P1
- Effort: M
- Risk: LOW
- Depends on: none
- Category: config / architecture
- Planned at: commit `451ea6a`, 2026-06-28

## Why this matters

HaxJobs decisions must come from the user's profile and preferences, not hardcoded Python. Current `haxjobs.toml` only stores paths/email/telegram. But discovery filters, classification, evaluator choice, target roles, work modes, and delivery channels all need one canonical config contract.

## Current state

`haxjobs.toml` currently has only:
- `[paths]`
- `[email]`
- `[telegram]`

`haxjobs_config.py` exposes only path/email/telegram constants. It does not expose job-search preferences, blacklists, target roles, level preferences, evaluator agent, or delivery config.

## Target design

Add config sections:

```toml
[user]
name = "Arinze Elenasulu"
location = "London, UK"
headline = "Python Backend Engineer | AI & Automation"

[job_search]
preferred_locations = ["London", "Remote UK", "Manchester", "Leeds"]
work_modes = ["remote", "hybrid", "onsite"]
employment_types = ["full_time", "contract", "graduate"]
target_levels = ["graduate", "junior", "mid"]
excluded_levels = ["senior", "lead", "principal", "staff", "manager"]
blacklisted_companies = []
blacklisted_keywords = ["sales", "marketing", "legal", "finance", "admin"]
lenient_filtering = true

[[roles]]
id = "backend_python"
label = "Python Backend Engineer"
cv_variant = "backend_python"
positive_keywords = ["python", "fastapi", "django", "postgresql", "api"]
negative_keywords = []
priority = 100

[evaluation]
agent = "hermes"
timeout_seconds = 180
levels.auto_pack = [1, 2]
levels.manual_review = [3]
levels.skip = [4]

[delivery]
channels = ["email"]
report_format = "markdown"
```

Keep it boring. TOML + stdlib parser only.

## Scope

In scope:
- `haxjobs.toml`
- `haxjobs_config.py`
- tests for config parsing

Out of scope:
- Changing classifier/evaluator behavior
- DB schema changes
- Scraper implementation

## Steps

### Step 1: Expand `haxjobs.toml`

Add `[user]`, `[job_search]`, `[[roles]]`, `[evaluation]`, `[delivery]`. Use the seven role IDs currently represented in `profile/role_taxonomy.json` as initial config data.

### Step 2: Expose parsed config in `haxjobs_config.py`

Add constants or helpers:
- `USER_PROFILE`
- `JOB_SEARCH_CONFIG`
- `ROLE_PROFILES`
- `EVALUATION_CONFIG`
- `DELIVERY_CONFIG`
- `EVALUATION_AGENT`
- `AUTO_PACK_LEVELS`
- `MANUAL_REVIEW_LEVELS`

Use plain dict/list objects from TOML. Do not create dataclasses yet unless tests prove it helps.

### Step 3: Add env overrides only where useful

Keep existing env overrides. Add only:
- `HAXJOBS_EVALUATION_AGENT`
- optionally `HAXJOBS_DELIVERY_CHANNELS`

Do not add env overrides for every array. YAGNI.

### Step 4: Add tests

Create `tests/test_haxjobs_config_profile.py`:
- TOML loads
- at least one `[[roles]]` exists
- every role has `id`, `cv_variant`, `positive_keywords`
- `EVALUATION_AGENT` defaults to configured agent
- `HAXJOBS_EVALUATION_AGENT` overrides it
- blacklisted companies list is available

## Done criteria

- `haxjobs.toml` contains profile/job_search/roles/evaluation/delivery sections.
- `haxjobs_config.py` exposes parsed role and job-search config.
- No code outside config is changed.
- New config tests pass.
- `python3 -m pytest -q` passes or stale tests are identified for the next plan.

## Stop conditions

Stop if you need to move profile facts out of existing JSON files. This plan adds config contract only; migration of old profile JSON is separate.
