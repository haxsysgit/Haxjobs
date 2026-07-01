# Plan 048: Job detail — JD viewer, evaluation breakdown, pack preview

> **Depends on**: 047 | **Priority**: P1 | **Effort**: M | **Risk**: LOW
> **Planned at**: commit `bf83142`, 2026-06-30

## Why this matters

When a user clicks a job, they need full context: job description, evaluation (why this score? what matches? what gaps?), and application pack. This is the decision-making screen.

## Steps

### Backend

1. Fill in `features/jobs/service.py` `get_job_detail()` — returns job + evaluation + pack metadata

### Frontend

2. `frontend/src/pages/JobDetailPage.tsx` with shadcn Tabs:
   - **Description tab**: full JD, company, location, source link, role family badge
   - **Evaluation tab**: fit score gauge, level badge, strongest matches (green cards), major gaps (amber cards), sponsorship risk, summary paragraph
   - **Pack tab**: file list (cover letter, CV, answers), "Download All" button, "Regenerate" button
3. Header: title, company, location badges, "Mark Applied" button (→ plan 049), "Skip" button

**shadcn components**: Tabs, Card, Badge, Button, Separator, Skeleton (loading state)

Custom `ScoreGauge` component: simple SVG radial showing score 0-100 with color (green ≥70, yellow ≥50, gray <50).

## Done criteria

- [ ] Job detail loads with 3 tabs
- [ ] Evaluation tab shows score, matches, gaps, summary
- [ ] Pack tab shows files with preview/download
- [ ] Apply and Skip buttons visible
