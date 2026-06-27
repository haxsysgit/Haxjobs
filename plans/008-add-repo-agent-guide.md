# Plan 008: Add repo agent guide

> **Executor instructions**: Follow this plan step by step. Run every verification command and confirm expected results. Stop on any STOP condition.
>
> **Drift check (run first)**: `git diff --stat b725a33..HEAD -- README.md docs .gitignore AGENTS.md CLAUDE.md`

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: plans/001-restore-verification-baseline.md
- **Category**: dx / docs
- **Planned at**: commit `b725a33`, 2026-06-27

## Why this matters

HaxJobs is agent-maintained and has sharp safety boundaries: Jade/local vs Archilles/live, runtime state ignored, Telegram only from Archilles, no unapproved outreach/apply actions, reusable CV variants, and SQLite as the target source of truth. There is no `AGENTS.md` or `CLAUDE.md` in the repo, so future agents can miss these rules and make unsafe changes.

## Current state

Relevant files:
- `README.md` — source of truth and checks.
- `docs/HAXJOBS_PRODUCT_SPEC.md` — product guardrails.
- `docs/HAXJOBS_RESET_PLAN.md` — reset rules.
- `.gitignore` — runtime/private boundary.
- No `AGENTS.md` or `CLAUDE.md` currently exists.

Current excerpts:
- `README.md:11-13`: local repo `/home/hax/haxjobs`, live repo `/home/hermes/haxjobs`, GitHub remote.
- `README.md:27-39`: runtime/private dirs ignored: `intake/`, `packs/`, `state/`, `reports/`, `outreach/`, DBs, `.env`, LinkedIn cookies.
- `docs/HAXJOBS_PRODUCT_SPEC.md:111-127`: automation ladder and approval requirements.
- `docs/HAXJOBS_PRODUCT_SPEC.md:261-265`: only Archilles sends Telegram messages.
- `docs/HAXJOBS_RESET_PLAN.md:87-116`: no per-job CV by default, SQLite source of truth, Telegram primary delivery, staged browser automation, no auto LinkedIn outreach.

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| Markdown sanity | `python3 - <<'PY'\nfrom pathlib import Path\nfor p in [Path('AGENTS.md')]:\n    text=p.read_text(); assert 'HaxJobs' in text; assert 'Do not' in text or 'Never' in text\nPY` | exit 0 |
| Git diff check | `git diff --check -- AGENTS.md README.md docs` | exit 0 |

## Scope

In scope:
- Create `AGENTS.md`
- Optionally add a one-line pointer in `README.md`

Out of scope:
- Editing source code.
- Creating separate Claude/Codex-specific guides unless requested.
- Adding secrets, tokens, private paths beyond already documented local/live repo paths.

## Git workflow

- Branch suggestion: `advisor/008-add-agent-guide`

## Steps

### Step 1: Create `AGENTS.md`

Write a concise repo-specific agent guide. Include:
- Project summary: discovery-first job-search automation/control surface.
- Local vs live: Jade `/home/hax/haxjobs`, Archilles `/home/hermes/haxjobs`, GitHub source of truth.
- Read/write boundaries: do not commit runtime dirs, DBs, `.env`, cookies, generated CV PDFs/HTML unless explicitly approved.
- Verification commands from README after Plan 001.
- Safety rules: no final submit, no LinkedIn connect/message, no outreach send, no Telegram send except Archilles path and explicit approval.
- Product rules: reusable CV variants, no per-job CV by default, pack generation/manual review gated, SQLite target source of truth.
- Coding style: readable Python/TypeScript, tests first, match existing temp DB test style.

Keep it practical. Do not paste huge docs. The guide should be short enough an executor actually reads it.

Verify: read the file and confirm the above bullets are present.

### Step 2: Link from README

Add a short line near setup/checks: “Agents should read `AGENTS.md` before changing code.” Do not rewrite the README.

Verify: `git diff --check -- AGENTS.md README.md` → exit 0.

## Test plan

Docs-only. No code tests required. Run diff check.

## Done criteria

- [ ] `AGENTS.md` exists and is repo-specific.
- [ ] It covers local/live workflow, runtime private dirs, safety approvals, verification commands, and product rules.
- [ ] README points agents to it.
- [ ] `git diff --check -- AGENTS.md README.md` exits 0.
- [ ] No source/runtime files are changed.
- [ ] `plans/README.md` row 008 updated when done.

## STOP conditions

Stop and report if:
- A `CLAUDE.md` or `AGENTS.md` appears after drift check with conflicting instructions.
- You are asked to include secrets or live tokens.

## Maintenance notes

Reviewers should keep this guide compact. If it grows into a duplicate of product docs, future agents will stop reading it.
