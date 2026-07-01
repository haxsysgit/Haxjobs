# Plan 038: Pre-restructure — signal repo is under construction

> **Executor instructions**: Follow this plan step by step. When done, update `plans/README.md`.
>
> **Drift check (run first)**: `head -5 README.md`
> If README already says "under construction" with warning banner, this plan may already be done.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: dx
- **Planned at**: commit `cf70638`, 2026-06-30

## Why this matters

Plans 040-056 will restructure the entire repo, swap the backend, rebuild the frontend, introduce a native agent, and ship to PyPI. During this time, anyone cloning the repo sees a flat directory of half-working Python scripts with no installable package. The README should warn that the repo is mid-migration so nobody tries to use it in its current state.

## Steps

1. Replace current README.md with a minimal version:

```markdown
# HaxJobs

> ⚠️ **Under construction** — HaxJobs is being rebuilt as a self-hosted job search platform.
> The current code is mid-migration. Nothing is installable. Come back when v1.0.0 ships.

HaxJobs is your personal job search platform. Upload your CV, discover matching jobs,
evaluate fit, generate application packs, and track every application. Self-hosted. Free. Open source.

**Coming in v1.0.0**: `uv tool install haxjobs && haxjobs start`

[Full documentation and screenshots will be added in plan 055.]
```

2. Commit:

```bash
git commit -m "signal repo is under construction before v1.0.0 restructure"
```

## Done criteria

- [ ] README.md shows "Under construction" warning at top
- [ ] No broken links or references to deleted features
