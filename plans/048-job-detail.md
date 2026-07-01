# Plan 048: Job detail — JD viewer, evaluation breakdown, pack preview

> **Depends on**: 047 | **Priority**: P1 | **Effort**: M | **Risk**: LOW
> **Planned at**: commit `bf83142`, 2026-06-30

## Why this matters

When a user clicks a job in the list, they need to see everything: full job description, the evaluation (why this score? what matches? what gaps?), and the application pack (cover letter, tailored CV). This is the decision-making screen.

## Steps

### Backend

1. `GET /api/jobs/:id/detail` — returns job + evaluation + pack status

### Frontend

2. `JobDetailPage.tsx` with tab layout (shadcn Tabs):
   - **Description tab**: full JD text, company, location, source link
   - **Evaluation tab**: fit score, level, match breakdown (strongest matches, major gaps), sponsorship risk, summary paragraph
   - **Pack tab**: show pack files (cover letter preview, CV preview, answers preview), "Download All" button, "Regenerate" button
3. Header bar: company logo placeholder, title, location badges, "Apply" button (→ decision loop, plan 049), "Skip" button
4. Match breakdown rendered as visual cards — not raw JSON

### Components

- shadcn Tabs for sections
- shadcn Card for match/gap items
- shadcn Badge for score/level
- Custom `ScoreGauge` component (simple radial or bar showing score 0-100)

## Done criteria

- [ ] Job detail page loads with 3 tabs
- [ ] Evaluation tab shows score, matches, gaps, summary
- [ ] Pack tab shows files with preview
- [ ] Apply and Skip buttons visible
