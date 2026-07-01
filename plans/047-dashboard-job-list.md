# Plan 047: Dashboard — job list with fit badges, filters, search

> **Depends on**: 041, 042, 045, 046 | **Priority**: P1 | **Effort**: L | **Risk**: LOW
> **Planned at**: commit `bf83142`, 2026-06-30

## Why this matters

The dashboard is the main screen — where users see all discovered jobs ranked by fit. This is the core UX. After onboarding, this is where users spend 90% of their time.

## Steps

### Backend (FastAPI routes)

1. `GET /api/jobs` — returns paginated job list with evaluations. Query params: `status`, `level`, `role_family`, `search`, `offset`, `limit`
2. `GET /api/jobs/:id` — returns single job with full evaluation detail
3. Wire existing `db/jobs.py` and `db/evaluations.py` into FastAPI routes (already have function logic)

### Frontend (React + shadcn/ui)

4. Replace `JobsPage.tsx` placeholder with real job list using shadcn DataTable
5. Each row: company, title, location, fit score badge (green L1, yellow L2, gray L3), source, discovered date
6. Sort by fit score (default), date, company
7. Filter by status (pending, evaluated, applied, skipped), level, role family
8. Search by title, company, or keyword in JD text
9. Click row → navigate to job detail (plan 048)
10. "Evaluate All Pending" button — triggers evaluation for all unevaluated jobs
11. Show counts: "47 jobs found, 23 evaluated, 5 applied"

### Components to use

- shadcn DataTable with column sorting, faceted filters, pagination
- Badge component for fit scores
- shadcn Command (cmd+k style search)

## Done criteria

- [ ] Job list shows real data from API
- [ ] Fit badges color-coded by level
- [ ] Filters work: status, level, role_family
- [ ] Search finds jobs by title/company
- [ ] Click row → navigates to detail
- [ ] Evaluate button triggers evaluation
