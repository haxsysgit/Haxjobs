# Plan 021: Delete stale tests and establish a clean test baseline

> Executor: run this plan before any implementation plans (015-019). A clean test suite means implementations can verify against reality, not stale expectations.
>
> Drift check: not applicable. This plan defines the cleanup, not implementation.

## Status

- Priority: P1
- Effort: M
- Risk: LOW (deleting only tests that test deleted code or wrong design)
- Depends on: none
- Category: tests
- Planned at: commit `451ea6a`, 2026-06-28

## Why this matters

After Stages 1-2 cleanup (discovery/ deleted, intake JSON removed) and the design clarification (profile-driven classification, agent-pluggable evaluation, template-fill packs), roughly half the 216 tests test code or design that no longer exists. Running them gives false confidence. A clean test baseline means when plans 015-019 are implemented, tests will fail because features are missing — not because tests test the wrong thing.

## Current state

Test file audit from this session:

**Valid tests (test code that still exists and matches design):**
- `test_evaluator_parsing.py` — JSON extraction/validation, needed regardless of agent
- `test_evaluation_writeback.py` — DB save_evaluation, path stays
- `test_application_templates.py` — template slot validation, stays
- `test_all_cv_variants.py` — CV variant validation, stays
- `test_cv_renderer.py` — HTML→PDF rendering, stays
- `test_cv_variant_registry.py` — registry, stays
- `test_api_security.py` — API security, stays
- `test_jobs_pagination.py` — pagination, stays
- `test_outreach_review.py` — outreach review, stays
- `test_pack_detail_api.py` — pack detail API, stays
- `test_pack_review_gate.py` — review gate, stays (needed for L3/L4)

**Stale tests (test deleted code or wrong design):**
- `test_role_family.py` — asserts hardcoded 7-role taxonomy. Wrong: classification should be profile-driven.
- `test_role_family_db.py` — tests DB columns for hardcoded role_family. Schema columns stay but classification source changes.
- `test_role_family_backfill_api.py` — backfills from hardcoded taxonomy. Wrong.
- `test_evaluator_pack_prompt.py` — tests hermes-specific build_prompt(). Wrong: prompt varies by agent.
- `test_generate_ready_packs.py` — tests per-job pack generation. Wrong: should fill templates.
- `test_pack_builder_templates.py` — tests build_job_pack creates full pack per job. Wrong: should fill slots.
- `test_pack_generator.py` — tests build_job_pack output. Wrong: template-fill, not full generation.
- `test_manual_pack_generation.py` — asserts all packs gated behind manual trigger. Wrong: L1/L2 auto.
- `test_run_pipeline_pack_hook.py` — asserts cron does NOT auto-generate packs. Wrong: L1/L2 should auto.
- `test_linkedin_import.py` — tests LinkedIn import (scraper deleted). Dead.

**Already deleted:**
- `test_intake_evaluation_flow.py` — deleted in Stage 2 (tested deleted evaluate_intake_file function)

## Steps

### Step 1: Delete tests that test fully deleted code

```bash
rm tests/test_linkedin_import.py
```

Verify: file gone, tests still pass (this test imports linkedin code that was deleted).

### Step 2: Delete tests that test the wrong design

These tests assert behavior that contradicts the current vision. They will be rewritten during plans 016-019, but right now they test wrong expectations:

```bash
rm tests/test_role_family.py
rm tests/test_role_family_db.py
rm tests/test_role_family_backfill_api.py
rm tests/test_evaluator_pack_prompt.py
rm tests/test_generate_ready_packs.py
rm tests/test_pack_builder_templates.py
rm tests/test_pack_generator.py
rm tests/test_manual_pack_generation.py
rm tests/test_run_pipeline_pack_hook.py
```

### Step 3: Run remaining tests and verify baseline

```bash
python3 -m pytest -q
```

Expected: all remaining tests pass (approximately 100-120 tests).

### Step 4: Record what was deleted so plans know what to rewrite

Create a note in `tests/README.md`:
```
# Test State (2026-06-28)

Tests deleted during cleanup wave — will be rewritten during plans 015-019:
- test_role_family.py, test_role_family_db.py, test_role_family_backfill_api.py → rewrite in plan 017
- test_evaluator_pack_prompt.py → rewrite in plan 017
- test_generate_ready_packs.py, test_pack_builder_templates.py, test_pack_generator.py → rewrite in plan 019
- test_manual_pack_generation.py, test_run_pipeline_pack_hook.py → rewrite in plan 019
- test_linkedin_import.py → rewrite in plan 015
- test_intake_evaluation_flow.py → already deleted, rewrite in plan 015/017
```

## Done criteria

- All stale test files deleted
- Remaining tests pass
- `tests/README.md` records what was deleted and which plan will rewrite it
- No test imports deleted functions or modules

## Stop conditions

Stop if deleting a test file causes cascading import failures in other test files. Investigate and report which tests depend on deleted imports.
