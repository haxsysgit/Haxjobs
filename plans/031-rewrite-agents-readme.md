# Plan 031: Rewrite AGENTS.md and README.md for the new product architecture

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat 51aad8a..HEAD -- AGENTS.md README.md docs/PRODUCT_ARCHITECTURE.md`
> If `AGENTS.md` or `README.md` have been modified since this plan was
> written, or `docs/PRODUCT_ARCHITECTURE.md` is absent, compare excerpts
> against live code. Major mismatch → STOP.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: LOW
- **Depends on**: 030
- **Category**: docs
- **Planned at**: commit `51aad8a`, 2026-06-30

## Why this matters

`AGENTS.md` is the first file every coding agent reads when working in this repo. `README.md` is the first thing a human sees. Both currently describe HaxJobs as "a black-box pipeline: jobs enter from discovery scrapers, everything else is automatic until the final report." That's the old system. The new vision is a self-hosted platform with onboarding, feedback loops, profile evolution, and outreach. Agents building the wrong thing is the most expensive mistake — these two files prevent it.

## Current state

Both files describe the old pipeline-only system:

- `AGENTS.md` — calls HaxJobs "Arinze's autonomous job discovery and application pipeline" and "a black-box pipeline." Lists `favorites`, `saved_jobs`, `evaluation_history` tables. References agent subprocess adapters. No mention of onboarding, decisions, learning, or outreach.
- `README.md` — same pipeline framing. Mentions "ship it as an installable pipeline that any agent can run" rather than a self-hosted web app.
- `docs/PRODUCT_ARCHITECTURE.md` — the canonical new vision. AGENTS.md and README.md must be consistent with it.

The repo conventions to match:
- `AGENTS.md` uses sections: What it does, Pipeline stages, Repo layout, Config, DB layout, Verification commands, Read/write boundaries, Safety rules, Product rules, Coding style.
- `README.md` uses short sections with code blocks for commands.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Verify no dead refs | `grep -rn "favorites\|saved_jobs\|evaluation_history" AGENTS.md README.md 2>/dev/null \|\| echo "CLEAN"` | CLEAN |
| Verify new terms present | `grep -c "onboarding\|profile evolution\|feedback loop\|outreach\|decision" AGENTS.md README.md` | positive count per file |

## Scope

**In scope**:
- `AGENTS.md` — full rewrite
- `README.md` — full rewrite

**Out of scope** (do NOT touch):
- `docs/PRODUCT_ARCHITECTURE.md` — read it for the vision, do not modify it
- Any other docs — they have their own plans
- Any source code — this is a docs-only change

## Git workflow

- Commit directly: `git commit -m "rewrite AGENTS.md and README.md for new product architecture"`
- One commit covering both files
- Do NOT push unless instructed

## Steps

### Step 1: Read the new product architecture

Read `docs/PRODUCT_ARCHITECTURE.md` in full. The rewrites must be consistent with:
- HaxJobs is a self-hosted job search platform (not a black-box pipeline)
- User journey: Onboard → Discover → Review → Apply → Learn → Repeat
- Onboarding wizard: CV upload → LLM extraction → guided questions → profile.json
- Feedback loop: user decides (apply/skip/reject) → system learns → profile evolves
- Outreach: find hiring managers, generate messages, track status
- Direct LLM API evaluation (not agent subprocess)
- Web UI on localhost:8241
- Cycle-based operation with learning between cycles

### Step 2: Rewrite AGENTS.md

Replace the entire file. The new AGENTS.md must follow the existing section structure but with updated content:

**Required sections and their key content:**

1. **What HaxJobs does** (replaces "black-box pipeline")
   - Self-hosted job search platform, runs at localhost:8241
   - Six phases: Onboard → Discover → Classify → Evaluate → Pack → Learn
   - Profile-driven: everything flows from `profile/arinze_profile.local.json`
   - Web UI for review, CLI for automation

2. **Pipeline stages** (updated)
   - 0. ONBOARDING — CV upload → LLM extraction → guided questions → profile.json (one-time)
   - 1. DISCOVERY — web search + ATS scrapers, profile-aware pre-filtering
   - 2. CLASSIFICATION — config-driven from haxjobs.toml
   - 3. EVALUATION — direct LLM API calls with JSON schema output
   - 4. PACK GENERATION — L1/L2 auto-pack, per-job CV review
   - 5. USER REVIEW — dashboard decision loop (apply/skip/reject)
   - 6. LEARNING — decisions feed back into profile preferences

3. **Repo layout** — keep the Jade/Archilles/GitHub table, update paths

4. **Config** — keep, accurate

5. **DB layout** — update to new model:
   - `discovered_jobs`, `jobs`, `evaluations` — keep
   - ADD: `decisions` (wired up), `cycle_state`, `job_history`, `learning_patterns`
   - REMOVE: `favorites`, `saved_jobs`, `evaluation_history` (replaced)
   - `outreach_drafts`, `outreach_contacts` — keep (being wired up)

6. **Verification commands** — keep as-is, still accurate

7. **Read/write boundaries** — keep, still accurate

8. **Safety rules** — keep, still accurate

9. **Product rules** — update:
   - Profile JSON is the backbone, built by onboarding wizard
   - Direct LLM API for evaluation (not agent subprocess)
   - Decisions drive the feedback loop
   - Keep the reusable CV variant rule

10. **Coding style** — keep, still accurate

### Step 3: Rewrite README.md

Replace the entire file. Shorter than AGENTS.md, aimed at humans:

```markdown
# HaxJobs

A self-hosted job search platform. Upload your CV, answer a few questions,
and HaxJobs discovers jobs, evaluates fit, generates application packs,
and gets smarter the more you use it.

## How it works

1. **Onboard** — upload CV, get a structured profile in minutes
2. **Discover** — scrapers + web search find jobs matching your profile
3. **Evaluate** — LLMs score every job against your full profile
4. **Pack** — auto-generated CVs and cover letters for good fits
5. **Decide** — apply, skip, or reject — the system learns
6. **Outreach** — find hiring managers, draft messages

## Quick start

```bash
pip install haxjobs        # (future — currently: uv run pipeline_db.py)
haxjobs start              # opens http://localhost:8241
```

## Config

`haxjobs.toml` is the canonical config. Everything is profile-driven.

## Development

```bash
./dev-app.sh start
PYTHONPATH=. python3 -m pytest -q tests/
```

## Docs

- `AGENTS.md` — guide for coding agents
- `docs/PRODUCT_ARCHITECTURE.md` — full product architecture
- `docs/DATA_MODEL.md` — database schema
```

### Step 4: Verify no references to deleted concepts

**Verify**: `grep -rn "favorites\|saved_jobs\|evaluation_history\|black-box\|autonomous pipeline" AGENTS.md README.md 2>/dev/null || echo "CLEAN"` → CLEAN

### Step 5: Verify new concepts are present

**Verify**:
```bash
grep -c "onboarding\|profile evolution\|feedback loop\|decision loop\|outreach" AGENTS.md
grep -c "self-hosted\|localhost:8241\|onboard" README.md
```
Both should return positive counts.

### Step 6: Commit

**Verify**: `git add AGENTS.md README.md && git commit -m "rewrite AGENTS.md and README.md for new product architecture"` → exit 0

## Test plan

No code tests needed — this is a docs-only change. Verification commands above serve as the test plan.

## Done criteria

- [ ] `AGENTS.md` describes onboarding, feedback loop, outreach, direct LLM API evaluation
- [ ] `AGENTS.md` does NOT mention favorites, saved_jobs, evaluation_history, black-box pipeline
- [ ] `README.md` describes a self-hosted platform, not a cron pipeline
- [ ] `README.md` references `docs/PRODUCT_ARCHITECTURE.md`
- [ ] Both files are internally consistent with each other
- [ ] `plans/README.md` status row updated to DONE

## STOP conditions

Stop and report back if:

- `docs/PRODUCT_ARCHITECTURE.md` does not exist — the vision document is required
- The drift check shows AGENTS.md or README.md were modified since this plan was written — they may already be updated
- You find references to entities not described in PRODUCT_ARCHITECTURE.md that you're unsure about — ask, don't guess

## Maintenance notes

These two files are the entry points for anyone (human or agent) encountering HaxJobs. When the product architecture changes in the future, update these first — they're the most-read files in the repo.
