# Plan 020: Full docs audit and alignment to current HaxJobs vision

> Executor: audit-only. Read every .md file, report staleness, update only what this plan approves.
>
> Drift check: not applicable — this is a docs plan, keyed to current HEAD.

## Status

- Priority: P2
- Effort: L
- Risk: LOW
- Depends on: none (can run before 015-019)
- Category: docs
- Planned at: commit `451ea6a`, 2026-06-28

## Why this matters

The HaxJobs vision was clarified in June 2026: discovery-first pipeline with automatic scrapers, profile-driven classification, pluggable agent evaluation, template-fill pack generation, and cycle markdown reports. The docs still describe an older design with manual entry, hardcoded role taxonomy, hermes-only evaluation, and gated manual packs. Stale docs are worse than no docs — they mislead any agent or human reading them.

## Current state

86 .md files exist in the repo (excluding .git, node_modules, .venv). Key docs that are likely stale:

Root:
- `README.md` — 1,555 bytes, likely describes old pipeline
- `AGENTS.md` — 2,988 bytes, agent guide
- `CV_FRAME_GOVERNANCE.md` — 25,759 bytes, CV governance

`docs/` directory:
- `ARCHITECTURE.md` — 3,338 bytes
- `APPLICATION_WORKFLOW.md` — 2,664 bytes
- `BROWSER_EXTENSION.md` — 1,907 bytes
- `DATA_MODEL.md` — 4,293 bytes
- `HAXJOBS_PRODUCT_SPEC.md` — 9,017 bytes
- `HAXJOBS_RESET_PLAN.md` — 14,251 bytes
- `HERMES_DIRECTION_BRIEF.md` — 1,653 bytes
- `HERMES_INTEGRATION.md` — 2,836 bytes
- `PRIVATE_ARCHILLES_UPDATE.md` — 3,131 bytes
- `PRIVATE_WORKFLOW_MAP.md` — 4,019 bytes
- `PRODUCT_VISION.md` — 2,932 bytes
- `PROFILE_DATA_SETUP.md` — 2,390 bytes
- `REPO_MAP.md` — 14,324 bytes
- `ROADMAP.md` — 17,019 bytes
- `SESSION_2026-06-11.md` — 4,059 bytes

Config/design:
- `haxjobs.toml` — current config, already migrated
- `haxjobs_config.py` — thin parser, already rewritten

Application templates (28 .md files under `application_templates/`):
- cover_letters, cv_variant_briefs, pack_templates — 7 per role family
- COVER_LETTER_GOVERNANCE.md, README.md

CV variants (14 .md files under `cv_variants/`):
- 7 role variants × cv_source.md + README.md

The current HaxJobs vision (as of June 2026):
1. Discovery: automatic scrapers → raw job ingestion with dedup/blacklist/filter hooks
2. Classification: profile-driven from haxjobs.toml, not hardcoded taxonomy
3. Evaluation: pluggable agent (hermes first), evaluated_jobs table
4. Pack generation: fill pre-existing role templates, auto for L1/L2, manual for L3/L4
5. Output: cycle markdown report with links, pack paths, fit analysis → DB → delivery

## Scope

In scope:
- Read every .md file under `docs/`, root, `cv_variants/`, `application_templates/`, `dashboard/`
- Classify each file as: keep-as-is, needs-update, delete
- Update files marked needs-update to match current vision
- Delete files that are session notes or superseded

Out of scope:
- `plans/*.md` — these are execution plans, managed separately
- `packs/**/*.md` — generated output, not docs
- `.venv/`, `node_modules/` — not our files
- Source code (.py, .tsx, .ts, .sh, .toml, .json) — docs only

## Steps

### Step 1: Audit every doc file

Read each of these files and classify:

**Root docs:**
- `README.md` — check if it describes discovery-first pipeline, profile-driven classification, pluggable agents, template-fill packs, cycle reports
- `AGENTS.md` — check if it mentions discovery scrapers, evaluated_jobs table, evaluate/ package, report delivery
- `CV_FRAME_GOVERNANCE.md` — check if CV variants are described as reusable templates

**`docs/` directory:**
- `PRODUCT_VISION.md` — should describe: black-box autonomous pipeline, little HITL, discovery→report cycle
- `HAXJOBS_PRODUCT_SPEC.md` — should match PRODUCT_VISION.md plus technical specifics
- `ARCHITECTURE.md` — should show: discovery → hooks → DB → classification → evaluation → pack → report
- `APPLICATION_WORKFLOW.md` — should match the current pipeline stages
- `DATA_MODEL.md` — should include discovered_jobs table, evaluations with agent/pack/report fields
- `ROADMAP.md` — should reflect plans 015-019 as next steps
- `REPO_MAP.md` — should not list discovery/ files that were deleted
- `HERMES_INTEGRATION.md` — should describe hermes as ONE evaluation agent, not the only agent
- `PRIVATE_ARCHILLES_UPDATE.md` — check relevance; may be Archilles-specific and can stay
- `PRIVATE_WORKFLOW_MAP.md` — check relevance
- `HAXJOBS_RESET_PLAN.md` — likely a one-time plan, can be deleted or moved to archive
- `SESSION_2026-06-11.md` — session notes, can be deleted
- `HERMES_DIRECTION_BRIEF.md` — check relevance
- `BROWSER_EXTENSION.md` — check if browser extension is still planned
- `PROFILE_DATA_SETUP.md` — check if profile setup changed with haxjobs.toml migration

**Application templates:**
- `COVER_LETTER_GOVERNANCE.md` — should reference template-fill approach
- `README.md` — check if it describes the pack generation flow

### Step 2: Update stale docs

For each file marked needs-update:
- Replace references to "intake JSON" with "discovered_jobs table"
- Replace references to "hardcoded role taxonomy" with "profile-driven from haxjobs.toml"
- Replace references to "evaluate_with_hermes.py" with "evaluate/ package with configured agent"
- Replace references to "generate new packs per job" with "fill pre-existing role templates"
- Add cycle report as the end-of-pipeline output
- Remove mentions of deleted files (cron/email_intake.py, cron/sync_db_to_intake.py, etc.)

### Step 3: Delete obsolete docs

Delete:
- `docs/SESSION_2026-06-11.md` — session notes, not permanent docs
- `docs/HAXJOBS_RESET_PLAN.md` — one-time plan, already executed or superseded
- Any doc that is a duplicate of another doc

### Step 4: Verify

- `grep -r 'intake JSON' docs/` returns zero matches (unless in historical context)
- `grep -r 'hardcoded.*taxonomy' docs/` returns zero matches (unless describing what was replaced)
- `grep -r 'evaluate_with_hermes' docs/` returns zero matches (unless describing the compatibility shim)
- Read `docs/PRODUCT_VISION.md` — confirms discovery→report pipeline
- Read `README.md` — describes the current project accurately

## Done criteria

- All `docs/*.md` files match the current HaxJobs vision (discovery-first, profile-driven, agent-pluggable, template-fill, cycle-report)
- Stale references to deleted files/old pipeline removed
- Session notes and one-time plans deleted
- `README.md` and `AGENTS.md` describe the current project
- No new .md files created outside docs/ or application_templates/ without reason

## Stop conditions

Stop if a doc describes a feature that hasn't been implemented yet and you're unsure whether to document it as planned or remove it. Mark it as "needs owner decision" and list it in a report.
