# Plan 030: Delete 7 docs superseded by new product architecture

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat 51aad8a..HEAD -- docs/`
> If `docs/PRODUCT_ARCHITECTURE.md` is absent or any of the files listed
> below have been modified since this plan was written, STOP.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: docs
- **Planned at**: commit `51aad8a`, 2026-06-30

## Why this matters

The new product architecture (`docs/PRODUCT_ARCHITECTURE.md`) redefines HaxJobs as a self-hosted platform with onboarding, feedback loops, and outreach. Seven existing docs describe the old pipeline-only system, operational notes for a single-user VPS setup, or hand-written profile procedures — all made obsolete by the new vision. They confuse agents and humans about what HaxJobs actually is.

## Current state

The following 7 files exist and should be deleted via `git rm`:

1. `docs/APPLICATION_WORKFLOW.md` — 75 lines about manual pack review gates and Telegram approval. Replaced by the dashboard decision loop in PRODUCT_ARCHITECTURE.md.
2. `docs/HERMES_DIRECTION_BRIEF.md` — 74 lines about Hermes integration. Replaced by direct LLM API evaluation (PRODUCT_ARCHITECTURE.md § Key Design Decisions #1).
3. `docs/HERMES_INTEGRATION.md` — 40 lines of `call_agent()` code docs. The subprocess agent pattern is replaced by direct API calls.
4. `docs/PRIVATE_ARCHILLES_UPDATE.md` — 95 lines of Archilles VPS operational notes. Single-user setup, not product docs.
5. `docs/PRIVATE_WORKFLOW_MAP.md` — 138 lines of LinkedIn scraping and cookie management workflow. Single-user operational notes.
6. `docs/PROFILE_DATA_SETUP.md` — 99 lines about hand-writing profile JSON. Replaced by the onboarding wizard (PRODUCT_ARCHITECTURE.md § Phase 1).
7. `docs/PRODUCT_VISION.md` — superseded by `docs/PRODUCT_ARCHITECTURE.md`. The old vision says "HaxJobs is an autonomous job discovery and application pipeline." The new vision says "HaxJobs is a self-hosted job search platform."

Verification that `PRODUCT_ARCHITECTURE.md` exists:
```bash
test -f docs/PRODUCT_ARCHITECTURE.md && echo "EXISTS" || echo "MISSING"
```

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Verify PRODUCT_ARCHITECTURE exists | `test -f docs/PRODUCT_ARCHITECTURE.md && echo OK` | OK |
| Delete files | `git rm docs/APPLICATION_WORKFLOW.md docs/HERMES_DIRECTION_BRIEF.md docs/HERMES_INTEGRATION.md docs/PRIVATE_ARCHILLES_UPDATE.md docs/PRIVATE_WORKFLOW_MAP.md docs/PROFILE_DATA_SETUP.md docs/PRODUCT_VISION.md` | exit 0, each file listed as `rm 'docs/...'` |
| Confirm deletions | `ls docs/APPLICATION_WORKFLOW.md docs/HERMES_DIRECTION_BRIEF.md docs/HERMES_INTEGRATION.md docs/PRIVATE_ARCHILLES_UPDATE.md docs/PRIVATE_WORKFLOW_MAP.md docs/PROFILE_DATA_SETUP.md docs/PRODUCT_VISION.md 2>&1` | all 7 return "No such file" |
| Ensure PRIVATE prefix in .gitignore | `grep -n "PRIVATE" .gitignore` | shows any existing PRIVATE gitignore rules |
| Verify docs/ dir | `ls docs/` | Lists remaining files (should include PRODUCT_ARCHITECTURE.md, ARCHITECTURE.md, DATA_MODEL.md, HAXJOBS_PRODUCT_SPEC.md, ROADMAP.md, REPO_MAP.md, diagrams/) |

## Scope

**In scope** (the only files to delete):
- `docs/APPLICATION_WORKFLOW.md`
- `docs/HERMES_DIRECTION_BRIEF.md`
- `docs/HERMES_INTEGRATION.md`
- `docs/PRIVATE_ARCHILLES_UPDATE.md`
- `docs/PRIVATE_WORKFLOW_MAP.md`
- `docs/PROFILE_DATA_SETUP.md`
- `docs/PRODUCT_VISION.md`

**Out of scope** (do NOT touch):
- `docs/PRODUCT_ARCHITECTURE.md` — this is the new canonical vision, keep it
- `docs/ARCHITECTURE.md` — handled by Plan 032
- `docs/DATA_MODEL.md` — handled by Plan 032
- `docs/HAXJOBS_PRODUCT_SPEC.md` — handled by Plan 033 (gets a header note)
- Any files outside `docs/`
- `.claude/skills/` — skills directory, not part of this cleanup

## Git workflow

- No branching needed — these are deletions, do them directly on the current branch
- Single commit: `git commit -m "delete 7 docs superseded by new product architecture"`
- Do NOT push unless instructed

## Steps

### Step 1: Verify PRODUCT_ARCHITECTURE.md exists

The new architecture doc must exist before we delete the old ones.

**Verify**: `test -f docs/PRODUCT_ARCHITECTURE.md && echo "OK"` → `OK`

### Step 2: Delete all 7 files in one git rm

**Verify**: `git rm docs/APPLICATION_WORKFLOW.md docs/HERMES_DIRECTION_BRIEF.md docs/HERMES_INTEGRATION.md docs/PRIVATE_ARCHILLES_UPDATE.md docs/PRIVATE_WORKFLOW_MAP.md docs/PROFILE_DATA_SETUP.md docs/PRODUCT_VISION.md` → exit 0

### Step 3: Confirm files are gone

**Verify**: `ls docs/APPLICATION_WORKFLOW.md 2>&1 | grep "No such file"` → exit 0 for all 7 paths

### Step 4: Verify no references to deleted files remain in other docs

Check that no remaining doc references the deleted files:

```bash
grep -r "APPLICATION_WORKFLOW\|HERMES_DIRECTION_BRIEF\|HERMES_INTEGRATION\|PRIVATE_ARCHILLES_UPDATE\|PRIVATE_WORKFLOW_MAP\|PROFILE_DATA_SETUP" docs/ README.md AGENTS.md PI_HANDOFF.md 2>/dev/null || echo "NO_REFS"
```

**Verify**: output is `NO_REFS` (or empty)

### Step 5: Commit

**Verify**: `git status --short` shows only the 7 deletions, then `git commit -m "delete 7 docs superseded by new product architecture"` → exit 0

## Done criteria

- [ ] All 7 files deleted via `git rm`
- [ ] `git status` shows no untracked docs outside the deletions
- [ ] No references to deleted files remain in remaining docs
- [ ] `plans/README.md` status row updated to DONE

## STOP conditions

Stop and report back if:

- `docs/PRODUCT_ARCHITECTURE.md` does not exist — do not delete old docs without the new one in place
- Any of the 7 files has been modified since this plan was written (drift check fails) — the content may have been updated to match the new vision
- A file outside the in-scope list shows as modified after the deletion — revert and report

## Maintenance notes

If any deleted doc contained information later needed (e.g., Archilles VPS setup), that information should be recreated as fresh operational docs under a separate directory, not restored as product documentation. These 7 files were product docs that misrepresented what HaxJobs is.
