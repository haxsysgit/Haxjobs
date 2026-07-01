# Plan 032: Rewrite ARCHITECTURE.md and update DATA_MODEL.md for new product

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat 51aad8a..HEAD -- docs/ARCHITECTURE.md docs/DATA_MODEL.md docs/PRODUCT_ARCHITECTURE.md`
> If either file was modified or PRODUCT_ARCHITECTURE.md is absent, STOP.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: LOW
- **Depends on**: 030
- **Category**: docs
- **Planned at**: commit `51aad8a`, 2026-06-30

## Why this matters

`docs/ARCHITECTURE.md` is the technical reference for how HaxJobs is built. It currently describes the old pipeline-only system — five stages, no onboarding, no feedback loop, no outreach engine. `docs/DATA_MODEL.md` describes tables including `favorites`, `saved_jobs`, and `evaluation_history` that the new product vision removes. Both must reflect the architecture in `PRODUCT_ARCHITECTURE.md`.

## Current state

- `docs/ARCHITECTURE.md` — 5-stage pipeline diagram, subprocess agent adapters, no onboarding/decisions/learning/outreach components. Mentions `favorites`/`saved_jobs` tables.
- `docs/DATA_MODEL.md` — accurate for current DB schema. Lists all 11 tables including `favorites`, `saved_jobs`, `evaluation_history`. Missing new tables: `cycle_state`, `job_history`, `learning_patterns`. Missing new columns on `jobs`: `applied_at`, `decision`, `decision_reason`, `cycle_id`.
- `docs/PRODUCT_ARCHITECTURE.md` — the canonical reference. Architecture section shows Web UI → API Server → Pipeline Engine → SQLite with 6 pipeline components including Outreach and Learning Engine. Data Model Changes section lists exactly what to add/remove/modify.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Verify no dead table refs | `grep -c "favorites\|saved_jobs\|evaluation_history" docs/ARCHITECTURE.md docs/DATA_MODEL.md` | 0 for ARCHITECTURE.md, handled in DATA_MODEL.md step |
| Verify new concepts | `grep -c "onboarding\|decision\|outreach\|learning\|cycle_state\|job_history" docs/ARCHITECTURE.md` | positive count |

## Scope

**In scope**:
- `docs/ARCHITECTURE.md` — full rewrite
- `docs/DATA_MODEL.md` — targeted updates (add new tables/columns, mark deprecated tables)

**Out of scope** (do NOT touch):
- `docs/PRODUCT_ARCHITECTURE.md` — read it, do not modify it
- Any source code — docs-only change
- The actual DB schema (`db/schema.py`) — this plan documents the target state, doesn't implement it

## Git workflow

- Commit directly: `git commit -m "rewrite ARCHITECTURE.md and update DATA_MODEL.md for new product"`
- One commit covering both files
- Do NOT push unless instructed

## Steps

### Step 1: Read the reference

Read `docs/PRODUCT_ARCHITECTURE.md` fully. Pay attention to:
- § Architecture — the component diagram (Web UI → API Server → Pipeline Engine → SQLite)
- § Key Design Decisions — especially #1 (direct LLM API), #2 (profile evolution), #3 (three data tiers)
- § Data Model Changes Needed — new tables, modified tables, tables to remove

### Step 2: Rewrite docs/ARCHITECTURE.md

Replace the entire file. The new structure:

**Architecture diagram** — ASCII art showing:
```
Web UI (React) → API Server (Python) → Pipeline Engine
                                          ├── Discovery
                                          ├── Classification
                                          ├── Evaluation (LLM API)
                                          ├── Pack Generation
                                          ├── Outreach Engine
                                          └── Learning Engine
                                       → SQLite Database
```

Not a 5-stage linear pipeline — a platform with components around a database.

**Sections to write:**

1. **What HaxJobs is** — self-hosted platform, not a pipeline. Web UI + API + engine + DB.
2. **Component architecture** — describe each box in the diagram:
   - Web UI: React dashboard, onboarding wizard, job review, outreach tracker
   - API Server: REST endpoints for profile, jobs, evaluations, decisions, outreach
   - Pipeline Engine: discovery, classification, evaluation (direct LLM API), pack gen, outreach, learning
   - SQLite: single-file DB with 3 data tiers (discovered_jobs, jobs, job_history)
3. **Key design decisions** — inline the 5 decisions from PRODUCT_ARCHITECTURE.md § Key Design Decisions
4. **User journey** — Onboard → Discover → Review → Apply → Learn → Repeat (from PRODUCT_ARCHITECTURE.md)
5. **Config architecture** — keep existing section, still accurate
6. **Directory map** — keep existing section, update for new components
7. **Data model** — brief reference to DATA_MODEL.md, list the 3 tiers

**Must NOT mention:**
- "black-box pipeline"
- `favorites`, `saved_jobs`, `evaluation_history` tables
- Agent subprocess adapters as the primary evaluation path
- "5 stages" — it's 6 phases now with onboarding and learning

### Step 3: Update docs/DATA_MODEL.md

Do NOT rewrite — this is an update. The file is mostly accurate. Make these targeted changes:

**Add new section before "Supporting tables":**

```markdown
### cycle_state

Tracks each pipeline run cycle.

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| cycle_id | TEXT UNIQUE | e.g. `2026-07-01` |
| started_at | TEXT | ISO-8601 |
| completed_at | TEXT | ISO-8601 |
| jobs_discovered | INTEGER | |
| jobs_evaluated | INTEGER | |
| packs_generated | INTEGER | |

### job_history

Permanent record of user actions on jobs.

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| job_id | INTEGER FK | Reference to jobs |
| action | TEXT | applied, rejected, skipped, archived |
| action_reason | TEXT | Why the user took this action |
| acted_at | TEXT | ISO-8601 |
| cycle_id | TEXT | Which cycle this happened in |

### learning_patterns

Learned preferences from user decisions.

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| pattern_type | TEXT | preferred_company, rejected_keyword, salary_trend, etc. |
| pattern_value | TEXT | The actual value |
| weight | REAL | Confidence 0.0-1.0 |
| evidence_count | INTEGER | How many decisions support this |
| updated_at | TEXT | ISO-8601 |
```

**Modify `jobs` table — add these columns to the existing table:**
```markdown
| applied_at | TEXT | ISO-8601, when user marked "apply" |
| decision | TEXT | apply, skip, reject, pending |
| decision_reason | TEXT | Why the user made this decision |
| cycle_id | TEXT | Which discovery cycle this job came from |
```

**Mark as DEPRECATED — add note above these tables:**
```markdown
> **Deprecated (will be removed)**: Replaced by the `decisions` table + `job_history` table.
```
Apply this note to: `favorites`, `saved_jobs`, `evaluation_history`.

**Update key relationships section** to include new tables:
```
discovered_jobs --(promoted)--> jobs
jobs --(evaluated)--> evaluations
jobs --(decided)--> decisions
decisions --(learned)--> learning_patterns
jobs --(archived)--> job_history
jobs --(outreach)--> outreach_drafts --> outreach_contacts
cycles captured in --> cycle_state
```

### Step 4: Verify ARCHITECTURE.md doesn't reference old concepts

**Verify**:
```bash
grep -c "favorites\|saved_jobs\|evaluation_history\|black-box\|5 stages\|agent subprocess" docs/ARCHITECTURE.md
```
Expected: 0 (every line returns 0)

### Step 5: Verify ARCHITECTURE.md references new concepts

**Verify**:
```bash
grep -c "onboarding\|Learning Engine\|Outreach Engine\|decision loop\|direct LLM API\|feedback" docs/ARCHITECTURE.md
```
Expected: positive counts for each

### Step 6: Verify DATA_MODEL.md has new tables

**Verify**:
```bash
grep -c "cycle_state\|job_history\|learning_patterns\|DEPRECATED" docs/DATA_MODEL.md
```
Expected: positive counts for each

### Step 7: Commit

**Verify**: `git add docs/ARCHITECTURE.md docs/DATA_MODEL.md && git commit -m "rewrite ARCHITECTURE.md and update DATA_MODEL.md for new product"` → exit 0

## Test plan

Docs-only change. Verification commands above serve as the test.

## Done criteria

- [ ] `docs/ARCHITECTURE.md` describes a platform with 6 components, not a 5-stage pipeline
- [ ] `docs/ARCHITECTURE.md` references direct LLM API evaluation, onboarding, learning engine, outreach engine
- [ ] `docs/ARCHITECTURE.md` does NOT mention favorites, saved_jobs, evaluation_history
- [ ] `docs/DATA_MODEL.md` includes `cycle_state`, `job_history`, `learning_patterns` tables
- [ ] `docs/DATA_MODEL.md` marks `favorites`, `saved_jobs`, `evaluation_history` as DEPRECATED
- [ ] `docs/DATA_MODEL.md` adds `applied_at`, `decision`, `decision_reason`, `cycle_id` to jobs table
- [ ] `plans/README.md` status row updated to DONE

## STOP conditions

Stop and report back if:

- `docs/PRODUCT_ARCHITECTURE.md` does not exist
- The drift check shows either file was modified since this plan was written
- You're unsure about a data model detail — PRODUCT_ARCHITECTURE.md § Data Model Changes Needed is the authority

## Maintenance notes

ARCHITECTURE.md and DATA_MODEL.md are reference docs. When the actual DB schema changes (future implementation plans), these docs must be updated to match. Don't let them drift — stale architecture docs are worse than no docs.
