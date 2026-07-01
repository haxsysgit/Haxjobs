# Plan 053: Documentation — README, quickstart, screenshots

> **Depends on**: 042-052 (everything visible exists) | **Priority**: P1 | **Effort**: M | **Risk**: LOW
> **Planned at**: commit `bf83142`, 2026-06-30

## Why this matters

When someone lands on the GitHub repo, the README is the product. It needs to show what HaxJobs does, how to install it (one command), and what it looks like (screenshots). Without this, it's just a pile of code.

## Steps

1. **Rewrite README.md** as product landing page:
   - Hero: "HaxJobs — your personal job search platform. Upload your CV, discover matching jobs, and track every application. Self-hosted. Free. Open source."
   - Quickstart: `pip install haxjobs && haxjobs start` → open localhost:8241
   - Screenshots: dashboard with job list, job detail with evaluation, onboarding wizard
   - Feature list with checkmarks
   - Tech stack badges
   - Link to full docs
   - License: MIT

2. **Screenshots**: take 4-6 screenshots of the running app (dashboard, job detail, evaluation, pack, profile, onboarding). Save to `docs/screenshots/`.

3. **Quickstart guide**: `docs/QUICKSTART.md` — step-by-step from zero to first job application. Include: install, open, upload CV, answer wizard questions, discover jobs, evaluate, review pack, mark as applied.

4. **Update docs/REPO_MAP.md** to match new structure

## Done criteria

- [ ] README.md shows: install command, screenshot, feature list
- [ ] Quickstart guide walks through full flow
- [ ] 4+ screenshots in docs/screenshots/
