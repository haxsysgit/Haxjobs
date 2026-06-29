# Plan 019: Auto-fill role pack templates for L1/L2 and generate cycle markdown report

> Executor: depends on Plans 016, 017, 018. This plan changes pack behavior and reporting only.
>
> Drift check: `git diff --stat 451ea6a..HEAD -- packs_builder/ generate_ready_packs.py application_templates/ db/ cron/ server/routes/ tests/`

## Status

- Priority: P1
- Effort: L
- Risk: MED
- Depends on: 016, 017, 018
- Category: product / automation
- Planned at: commit `451ea6a`, 2026-06-28

## Why this matters

The intended HaxJobs output is mostly autonomous. L1 and L2 jobs should automatically get application material by filling pre-existing role templates. L3/L4 jobs should not auto-generate full packs; they should appear in the cycle report for review or skip. The cycle ends with a markdown report listing evaluated jobs, fit reasons, links, and pack paths, delivered through configured channels.

## Current state

- `packs_builder/job_pack.py` builds per-job markdown files from scratch: `fit_report.md`, `cover_letter.md`, `field_answers.md`, `interview_questions.md`, `telegram_summary.md`, `metadata.json`.
- It references role templates under `application_templates/cover_letters/`, but still writes a new per-job pack folder.
- `generate_ready_packs.py` is a manual/gated process.
- `test_manual_pack_generation.py` and `test_run_pipeline_pack_hook.py` assert packs are not automatic.
- There is no cycle markdown report table or delivery flow.

## Target design

1. Each configured role has a reusable pack template.
2. Evaluation L1/L2 automatically fills slots in that template:
   - company
   - role_title
   - hiring_manager_or_team
   - jd_match_points
   - company_reason
   - evidence_story
   - gap_note
   - links and metadata
3. Output can still be per job, but it is a rendered copy of a reusable template, not an agent-generated bespoke pack.
4. L3/L4 jobs are not auto-packed. They are included in the cycle report.
5. At end of a pipeline cycle, generate `reports/<cycle>.md` and save report body/path to DB.
6. Delivery uses configured `[delivery]` channels. First implementation can write markdown only; email/messaging can be a later adapter if not already wired safely.

## Scope

In scope:
- `packs_builder/job_pack.py`
- `generate_ready_packs.py` or replacement `generate_packs_for_evaluations.py`
- `application_templates/`
- new `reports/` module or `cron/generate_cycle_report.py`
- DB fields from Plan 018
- tests for L1/L2 auto-pack and report markdown

Out of scope:
- Actually sending email/messages if no safe delivery adapter exists
- 3-agent simulation loop
- Creating new CV variants

## Steps

### Step 1: Rename behavior, not necessarily files

Keep `packs_builder/job_pack.py` if cheaper, but update docstrings and tests: it fills templates for a job. It should not pretend to generate a new custom application from scratch.

### Step 2: Make template slots explicit

For each role template, require the slots:
- `{hiring_manager_or_team}`
- `{role_title}`
- `{company}`
- `{jd_match_points}`
- `{company_reason}`
- `{evidence_story}`
- `{gap_note}`

If a slot is missing, fail loudly.

### Step 3: Auto-pack only configured levels

Read `AUTO_PACK_LEVELS` from config. Default from Plan 016: `[1, 2]`.

During evaluation pipeline, after saving an evaluation:
- if `level in AUTO_PACK_LEVELS`, render pack template and update evaluation/job pack path
- if level 3/4, do not generate pack

### Step 4: Rewrite stale tests

Rewrite tests that currently assert manual-only packs:
- `test_manual_pack_generation.py`: L3/L4 require manual review; L1/L2 auto-pack is allowed/expected.
- `test_run_pipeline_pack_hook.py`: cron/pipeline should auto-pack L1/L2 after evaluation.
- `test_pack_builder_templates.py`: assert output is filled template, not generic generated prose.

### Step 5: Add cycle report generator

Create a simple module, e.g. `reports/cycle_report.py`:
- query jobs + evaluations for this run/cycle
- write markdown with sections:
  - summary counts
  - L1/L2 packed jobs with links and pack paths
  - L3 manual review jobs
  - L4 skipped jobs with reasons
- save report path/body to DB using fields from Plan 018 or a small `reports` table if needed

### Step 6: Wire report generation into cron

At end of `cron/run_pipeline.sh`, call report generator after evaluation/classification/pack generation.

If delivery isn't implemented safely yet, write the report and print the path. Do not fake email/messaging delivery.

## Tests

Add/update:
- `tests/test_auto_pack_levels.py`
- `tests/test_pack_template_slot_fill.py`
- `tests/test_cycle_report.py`

Cases:
- L1/L2 evaluation creates pack path
- L3/L4 does not create pack path
- template slots are all filled, no `{slot}` leftovers
- cycle report includes job title, company, URL, fit score, pack path when present
- report generator writes markdown and stores path/body in DB

## Done criteria

- L1/L2 jobs auto-fill packs from reusable templates.
- L3/L4 jobs do not auto-generate full packs.
- Existing manual review remains available for L3/manual cases.
- Cycle markdown report is written under `reports/` and saved to DB.
- Tests reflect the real automation design, not old manual-only pack gating.
- `python3 -m pytest -q` passes.

## Stop conditions

Stop if email/messaging delivery requires secrets or live external sends. Produce report file only and document delivery as a follow-up.
