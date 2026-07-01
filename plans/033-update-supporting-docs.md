# Plan 033: Update supporting docs — roadmap, repo map, handoff, env, scripts, product spec

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat 51aad8a..HEAD -- docs/ROADMAP.md docs/REPO_MAP.md PI_HANDOFF.md .env.example scripts/README.md docs/HAXJOBS_PRODUCT_SPEC.md`
> If any file was modified since this plan was written, STOP.

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: LOW
- **Depends on**: 030, 031, 032
- **Category**: docs
- **Planned at**: commit `51aad8a`, 2026-06-30

## Why this matters

Six supporting docs are now inconsistent with `PRODUCT_ARCHITECTURE.md`. ROADMAP.md lists plans 015-026 as the future. REPO_MAP.md describes an old file layout. PI_HANDOFF.md is a 9.6KB handoff document describing the old system in detail. `.env.example` is missing new product env vars. `scripts/README.md` only lists one script. `HAXJOBS_PRODUCT_SPEC.md` is a valuable precursor to the new vision but needs a header noting it's historical.

## Current state

- `docs/ROADMAP.md` — lists plans 015-026 as current, references deleted docs (CV_FRAME_GOVERNANCE)
- `docs/REPO_MAP.md` — 137-line file inventory, references old patterns, mentions deleted files
- `PI_HANDOFF.md` — 9.6KB, describes pipeline-only system, lists plans 001-022, references deleted files and old architecture. This is the most dangerous stale doc — it's designed to onboard a new agent and will mislead them.
- `.env.example` — 28 lines, covers paths and user profile but missing LLM API keys and onboarding config
- `scripts/README.md` — 14 lines, only mentions `walkthrough_evaluator.py` but there are more scripts
- `docs/HAXJOBS_PRODUCT_SPEC.md` — 2026-06-11 spec that predicted much of the new vision. Valuable but needs a header.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Verify PI_HANDOFF references new concepts | `grep -c "onboarding\|feedback loop\|outreach\|PRODUCT_ARCHITECTURE" PI_HANDOFF.md` | positive counts |
| Verify .env.example has new vars | `grep -c "LLM\|OPENAI\|ANTHROPIC\|ONBOARDING" .env.example` | positive counts |
| Verify ROADMAP references wave 6 | `grep -c "Wave 6\|onboarding\|feedback" docs/ROADMAP.md` | positive counts |

## Scope

**In scope**:
- `docs/ROADMAP.md` — rewrite
- `docs/REPO_MAP.md` — update
- `PI_HANDOFF.md` — rewrite
- `.env.example` — update
- `scripts/README.md` — update
- `docs/HAXJOBS_PRODUCT_SPEC.md` — add historical header

**Out of scope**:
- `docs/PRODUCT_ARCHITECTURE.md` — reference only
- Any other docs
- Any source code

## Git workflow

- Commit directly after all 6 files are done: `git commit -m "update supporting docs for new product architecture"`
- One commit for all files
- Do NOT push unless instructed

## Steps

### Step 1: Read PRODUCT_ARCHITECTURE.md

### Step 2: Rewrite docs/ROADMAP.md

Replace entire file. New content:

```markdown
# HaxJobs Roadmap

The current product architecture is documented in `PRODUCT_ARCHITECTURE.md`.
Implementation plans are tracked in `plans/README.md`.

## Completed (Waves 1-5)

All 29 plans from waves 1-5 are DONE. These built the pipeline infrastructure:
discovery scrapers, config-driven classification, pluggable evaluation,
auto-pack generation, cycle reports, and multi-agent adapter research.

## Wave 6 — Product Foundation (current)

Make HaxJobs a usable product:
- Direct LLM API evaluation (replace agent subprocess)
- Onboarding wizard (CV upload → profile extraction → guided questions)
- Profile evolution (fields that update based on usage)
- Decision loop (apply/skip/reject from dashboard)

See `plans/README.md` for specific plan numbers when created.

## Wave 7 — Learning & Outreach

Make HaxJobs smart:
- Learning engine (processes decisions, evolves preferences)
- Outreach engine (hiring manager discovery, message generation)
- DB lifecycle (cycle tracking, job archiving, cleanup)

## Wave 8 — Polish & Ship

Make HaxJobs a product anyone can use:
- Product packaging (pip install haxjobs)
- Web search discovery (beyond ATS scrapers)
- Comprehensive testing
```

### Step 3: Update docs/REPO_MAP.md

Don't rewrite — update specific sections:

**Replace the "What HaxJobs is" section** (first paragraph) with:
```
HaxJobs is a self-hosted job search platform. See `PRODUCT_ARCHITECTURE.md`
for the full vision and `AGENTS.md` for the agent guide.
```

**Update directory map** to reflect current layout:
- Add: `evaluate/agents/` — evaluation adapter implementations
- Add: `discovery/scrapers/` — Greenhouse, Ashby, Lever scrapers
- Add: `docs/PRODUCT_ARCHITECTURE.md` — canonical product architecture
- Remove: references to deleted files from plan 025 (cv_generate.py, cv_validator.py, pack_builder.sh, etc.)
- Remove: `profile/role_taxonomy.json` — deleted, role taxonomy is TOML-driven
- Remove: references to `intake/` as active — it's a runtime dir and gitignored

**Update "Key files" section** to list:
```
haxjobs.toml — canonical config
profile/arinze_profile.local.json — profile backbone
AGENTS.md — agent guide
docs/PRODUCT_ARCHITECTURE.md — product architecture
docs/ARCHITECTURE.md — technical architecture
docs/DATA_MODEL.md — database schema
```

### Step 4: Rewrite PI_HANDOFF.md

Replace entire file. This is the comprehensive handoff for Pi coding agent.

Structure it as:
```markdown
# HaxJobs — Pi Handoff

## What HaxJobs is
[2-3 sentences from PRODUCT_ARCHITECTURE.md — self-hosted platform, not pipeline]

## Product architecture
[Link to docs/PRODUCT_ARCHITECTURE.md — say "read this first"]
[Brief summary of the 6 phases]

## Current state
[What's built: discovery scrapers, classification, evaluation, pack gen, cycle reports, dashboard shell, profile JSON]
[What's NOT built: onboarding wizard, decision loop, learning engine, outreach engine, product packaging]
[Config: haxjobs.toml + haxjobs_config.py]
[DB: SQLite, 11 tables, some deprecated (favorites, saved_jobs, evaluation_history)]

## Repo conventions
[Same as AGENTS.md coding style section — Python stdlib, SQLite no ORM, Bash set -euo pipefail, etc.]

## Key files
[Table of critical files and what they do]

## Verification commands
[Same as AGENTS.md — PYTHONPATH=. pytest, py_compile, bash -n, dashboard tsc/lint/build]

## Read/write boundaries
[Same as AGENTS.md]

## Safety rules
[Same as AGENTS.md]

## What to work on next
[Reference plans/README.md for wave 6 plans]
```

The key difference from the old PI_HANDOFF.md: it must describe the NEW product architecture, not the old pipeline. It must reference `PRODUCT_ARCHITECTURE.md` as the canonical vision.

### Step 5: Update .env.example

Keep all existing vars. Add these new sections:

```bash
# ── LLM API keys (for direct evaluation) ──
# HAXJOBS_OPENAI_API_KEY=sk-...
# HAXJOBS_ANTHROPIC_API_KEY=sk-ant-...
# HAXJOBS_LLM_PROVIDER=openai          # openai | anthropic
# HAXJOBS_LLM_MODEL=gpt-5.5            # model to use for evaluation

# ── Onboarding ──
# HAXJOBS_ONBOARDING_ENABLED=true       # show onboarding wizard on first run

# ── API server ──
# HAXJOBS_API_HOST=127.0.0.1
# HAXJOBS_API_PORT=8241
```

### Step 6: Update scripts/README.md

Replace with:
```markdown
# Scripts

Utility scripts for development and debugging.

| Script | Purpose |
|--------|---------|
| `walkthrough_evaluator.py` | Step-by-step evaluator walkthrough — shows how prompt building, LLM calls, and parsing work |
| `dev-app.sh` | Start backend API + frontend dashboard for local development |

Usage:
```bash
python3 scripts/walkthrough_evaluator.py --quick       # evaluate a job
python3 scripts/walkthrough_evaluator.py --dry-run     # show prompt without LLM call
python3 scripts/walkthrough_evaluator.py --adapter hermes --job 625
```
```

### Step 7: Add header to docs/HAXJOBS_PRODUCT_SPEC.md

Prepend at the very top of the file (before the title):

```markdown
> **Historical document** — written 2026-06-11. This spec predicted many
> features of the current product architecture (profile building, outreach,
> networking, automation ladder, decision tracking) before they were formally
> designed. The canonical vision is now `PRODUCT_ARCHITECTURE.md`. Keep this
> as a record of the original product thinking.
```

Use `sed` to insert at line 1:
```bash
sed -i '1i\> **Historical document** — written 2026-06-11. This spec predicted many features of the current product architecture (profile building, outreach, networking, automation ladder, decision tracking) before they were formally designed. The canonical vision is now `PRODUCT_ARCHITECTURE.md`. Keep this as a record of the original product thinking.\n' docs/HAXJOBS_PRODUCT_SPEC.md
```

### Step 8: Verify all files

Run all verification greps:

```bash
# ROADMAP.md: references wave 6 product foundation
grep -c "Wave 6\|Product Foundation\|onboarding" docs/ROADMAP.md

# REPO_MAP.md: no dead file references, has new architecture
grep -c "PRODUCT_ARCHITECTURE\|evaluate/agents\|discovery/scrapers" docs/REPO_MAP.md
grep -c "cv_generate.py\|cv_validator.py\|pack_builder.sh\|role_taxonomy.json" docs/REPO_MAP.md  # should be 0

# PI_HANDOFF.md: references new vision, not old pipeline
grep -c "PRODUCT_ARCHITECTURE\|onboarding\|feedback loop" PI_HANDOFF.md
grep -c "black-box\|autonomous pipeline" PI_HANDOFF.md  # should be 0

# .env.example: has new vars
grep -c "LLM\|OPENAI\|ONBOARDING" .env.example

# HAXJOBS_PRODUCT_SPEC.md: has historical header
head -3 docs/HAXJOBS_PRODUCT_SPEC.md | grep -c "Historical document"
```

All should return positive counts (except the ones marked "should be 0").

### Step 9: Commit

**Verify**: `git add docs/ROADMAP.md docs/REPO_MAP.md PI_HANDOFF.md .env.example scripts/README.md docs/HAXJOBS_PRODUCT_SPEC.md && git commit -m "update supporting docs for new product architecture"` → exit 0

## Test plan

Docs-only change. Grep verifications in Step 8 serve as the test.

## Done criteria

- [ ] `docs/ROADMAP.md` shows Wave 6-8 product phases, not old plans 015-026
- [ ] `docs/REPO_MAP.md` reflects current file layout with no dead file references
- [ ] `PI_HANDOFF.md` describes new product architecture, references PRODUCT_ARCHITECTURE.md
- [ ] `.env.example` includes LLM API key and onboarding env vars
- [ ] `scripts/README.md` lists both scripts with usage examples
- [ ] `docs/HAXJOBS_PRODUCT_SPEC.md` has historical header at top
- [ ] `plans/README.md` status row updated to DONE

## STOP conditions

Stop and report back if:

- `docs/PRODUCT_ARCHITECTURE.md` does not exist
- Any file in scope has been modified since plan was written (drift check)
- Plans 030, 031, or 032 are not DONE — this plan depends on their doc changes

## Maintenance notes

PI_HANDOFF.md should be regenerated after each major wave of changes. It's the onboarding document for new agents working in the repo — when it's stale, agents build the wrong thing.
