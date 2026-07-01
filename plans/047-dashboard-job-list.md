# Plan 047: Dashboard — job list with fit badges, filters, search

> **Depends on**: 041, 042, 045, 046 | **Priority**: P1 | **Effort**: L | **Risk**: LOW
> **Planned at**: commit `bf83142`, 2026-06-30

## Why this matters

The dashboard is the main screen. After onboarding, users spend 90% of their time here — browsing jobs ranked by fit, filtering, and clicking into details.

## Steps

### Backend: features/jobs/

1. **service.py**: wire existing `db/jobs.py` + `db/evaluations.py` functions
   - `list_jobs(status, level, role_family, search, offset, limit)` — paginated, filtered, sorted by fit_score DESC
   - `get_job_detail(job_id)` — job + evaluation + pack status
2. **routes.py**:
   - `GET /api/jobs` — query params: status, level, role_family, search, offset, limit
   - `GET /api/jobs/{id}` — full detail
3. **schemas.py**: `JobListParams`, `JobListResponse`, `JobDetailResponse`

### Frontend: JobsPage

4. Replace placeholder with shadcn DataTable
5. Columns: company, title, location, fit badge (green L1, yellow L2, gray L3), source, date
6. Sort by fit score (default), date, company
7. Faceted filters: status, level, role_family
8. Search input — filters by title or company (client-side from loaded data, or server-side query param)
9. "Evaluate All Pending" button → `POST /api/evaluation/run`
10. Click row → navigate to `/jobs/{id}`
11. Show counts: "47 jobs, 23 evaluated, 5 applied"

**shadcn components**: DataTable (column-header, pagination, toolbar, faceted-filter, view-options), Badge, Button, Input

## Done criteria

- [ ] Job list shows real data from API
- [ ] Fit badges color-coded by level
- [ ] Filters work: status, level, role_family
- [ ] Search finds by title/company
- [ ] Click row → navigate to detail
- [ ] Evaluate button triggers evaluation
- [ ] `npx tsc -b --noEmit` passes
