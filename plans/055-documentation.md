# Plan 055: Documentation — README, quickstart, screenshots

> **Depends on**: 049 through 054 | **Priority**: P1 | **Effort**: M | **Risk**: LOW
> **Planned at**: commit `bf83142`, 2026-06-30

> ⚠️ **PLANS ARE NOT FINAL** — review against current project reality before implementing.
> Every plan was drafted at a point in time. File paths, function signatures, dependency
> versions, and architecture decisions may have changed since. If the plan says
> `run_structured()` but the codebase has `run() + extract_json()`, follow the codebase.
> If the plan references a deleted file, skip that step. Use these plans as guidance,
> not gospel.

## Why this matters

When someone lands on the GitHub repo, the README is the product. It shows what HaxJobs does, how to install it (one command), and what it looks like.

## Steps

1. **Rewrite README.md**:
   - Hero: "HaxJobs — your personal job search platform. Upload your CV, discover matching jobs, and track every application. Self-hosted. Free. Open source."
   - Quickstart: `uv tool install haxjobs && haxjobs start` → open localhost:8241
   - Screenshots: dashboard, job detail with evaluation, onboarding wizard
   - Feature list: CV extraction, job discovery, fit scoring, application packs, decision tracking
   - Tech stack badges: Python, FastAPI, React, shadcn/ui, SQLite
   - "Built with uv" mention
   - License: MIT

2. **Screenshots**: take 4-6 screenshots of the running app. Save to `docs/screenshots/`.

3. **Quickstart guide** `docs/QUICKSTART.md`:
   - Prerequisites: Python 3.12+, uv, Node.js 18+ (for frontend dev)
   - Install: `uv tool install haxjobs`
   - Start: `haxjobs start`
   - Walkthrough: upload CV → answer wizard → discover jobs → evaluate → review pack → mark applied

4. **Update docs/REPO_MAP.md** for new structure

5. **Keep agent architecture docs linked**: ensure README or `docs/REPO_MAP.md` points to `docs/PI_HAXJOBS_INTERNALS_MAPPING.md` for the native agent design.

## Deliverable report (required)

After implementation, the executor must produce a compact report:

- **What changed**: files created, modified, deleted
- **Deliverables**: endpoints, pages, CLI commands the user can now use
- **How to verify**: the exact commands that prove it works
- **Deviations from plan**: what the plan said vs what was actually done
- **What was skipped**: and the reason (YAGNI, blocked, deferred)

## Done criteria

- [ ] README.md shows: install command, screenshot, feature list
- [ ] Quickstart walks through full flow
- [ ] 4+ screenshots in docs/screenshots/
- [ ] Native agent docs link to `docs/PI_HAXJOBS_INTERNALS_MAPPING.md`
