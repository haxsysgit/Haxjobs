# Plan 017: Make classification profile-driven and evaluation agent-pluggable

> Executor: depends on Plan 016. Do not change pack generation/report delivery here.
>
> Drift check: `git diff --stat 451ea6a..HEAD -- evaluation/role_family.py evaluate_with_hermes.py haxjobs_config.py pipeline_db.py tests/`

## Status

- Priority: P1
- Effort: L
- Risk: MED
- Depends on: 016
- Category: architecture / migration
- Planned at: commit `451ea6a`, 2026-06-28

## Why this matters

Classification currently depends on static role taxonomy and hardcoded tie-break nudges. Evaluation currently depends on the Hermes CLI. The intended design is: role families come from the user's configured profile/preferences, and evaluation can use whichever agent is configured.

## Current state

- `evaluation/role_family.py` loads `profile/role_taxonomy.json` by default.
- `_ROLE_TIEBREAK_ORDER` is hardcoded to seven role IDs.
- `_score_family()` contains product-specific nudges for hardcoded families.
- `evaluate_with_hermes.py` sets `HERMES_BIN = "hermes"` and calls `[HERMES_BIN, "chat", "--yolo", "-Q", "-q", prompt]`.
- Tests like `test_role_family.py` assert a hardcoded set of seven families.

## Target design

1. Classification reads roles from `haxjobs_config.ROLE_PROFILES`.
2. Role ordering is config priority, not hardcoded list.
3. Scoring remains deterministic keyword matching for now.
4. Evaluators move into an `evaluate/` package:
   - `evaluate/common.py` — prompt building, JSON extraction, validation schema
   - `evaluate/agents/hermes.py` — Hermes CLI adapter
   - future adapters fit same tiny interface
   - `evaluate/run.py` or `evaluate_job.py` selects adapter from `haxjobs.toml`
5. Existing CLI behavior can stay as a wrapper, but filename should no longer define the product. `evaluate_with_hermes.py` becomes either deleted or a compatibility shim.

## Scope

In scope:
- `evaluation/role_family.py`
- `evaluate/` package creation
- `evaluate_with_hermes.py` compatibility wrapper or replacement
- `pipeline_db.py` calls if they reference old evaluator name
- tests for config-driven classification and agent selection

Out of scope:
- Changing evaluation scoring prompt deeply
- Pack generation
- Report delivery
- 3-agent simulation loop

## Steps

### Step 1: Rewrite classifier source of truth

Change `load_role_taxonomy()` or add `load_role_profiles()` so it can use `haxjobs_config.ROLE_PROFILES` by default.

Remove `_ROLE_TIEBREAK_ORDER`. Tie-break by configured `priority` descending, then role order in TOML.

Remove hardcoded family-specific nudges. If a nudge matters, it belongs in the role's keywords in TOML.

### Step 2: Rewrite role tests

Replace `test_role_family.py` expectations:
- do not assert exact hardcoded set unless reading it from TOML
- assert every configured role can be loaded
- assert a sample backend job maps to the role whose config contains backend/Python keywords
- assert unknown/non-tech role returns unknown or filtered outcome according to config

### Step 3: Create `evaluate/` package

Minimum files:
- `evaluate/__init__.py`
- `evaluate/common.py` — move `EXPECTED_SCHEMA`, `extract_json()`, `validate_result()`, `build_prompt()` here
- `evaluate/agents/hermes.py` — `evaluate(prompt, timeout_seconds) -> str`
- `evaluate/run.py` — CLI and DB evaluation flow, selects adapter based on `EVALUATION_AGENT`

Keep adapter interface tiny. No class hierarchy unless needed:
```python
def call_agent(prompt: str, *, timeout_seconds: int) -> str: ...
```

### Step 4: Keep compatibility wrapper

Either leave `evaluate_with_hermes.py` as:
```python
#!/usr/bin/env python3
from evaluate.run import main
raise SystemExit(main())
```
Or update `cron/run_pipeline.sh` to call the new path and delete old file. Prefer wrapper for lower blast radius.

### Step 5: Add evaluator tests

Create or rewrite:
- `tests/test_evaluator_agent_selection.py`
- `tests/test_evaluator_parsing.py` imports from `evaluate.common`, not `evaluate_with_hermes`

Test cases:
- configured `agent = "hermes"` selects Hermes adapter
- unknown agent errors clearly
- parsing/validation still works

## Done criteria

- Role classification reads from TOML config, not `profile/role_taxonomy.json` by default.
- No hardcoded role-family tie-break list remains.
- `evaluate/` package exists with common + agent adapter split.
- Configured `evaluation.agent` controls adapter selection.
- `evaluate_with_hermes.py` is either a shim or removed with all callers updated.
- Stale tests for hardcoded taxonomy are rewritten.
- `python3 -m pytest -q` passes.

## Stop conditions

Stop if a non-Hermes adapter requires a real external dependency. This plan only creates the adapter seam and keeps Hermes working.
