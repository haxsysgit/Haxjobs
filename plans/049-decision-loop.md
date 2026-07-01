# Plan 049: Decision loop — mark applied/skipped/rejected

> **Depends on**: 048 | **Priority**: P1 | **Effort**: S | **Risk**: LOW
> **Planned at**: commit `bf83142`, 2026-06-30

## Why this matters

The `decisions` table already exists in the schema. `db/decisions.py` has functions. `tests/test_decisions.py` has 10 tests. But nothing calls them from the API or UI. This plan closes the feedback loop — users mark what they did with each job, and HaxJobs tracks it.

## Steps

### Backend

1. `POST /api/jobs/:id/decision` — body: `{"decision": "applied|skipped|rejected", "notes": "..."}`
2. `GET /api/jobs/:id/decisions` — returns decision history for this job
3. Wire existing `db/decisions.py` functions into the route

### Frontend

4. Decision buttons on job detail page (already have Apply/Skip buttons from plan 048)
5. Click Apply → modal asking for date applied + optional notes → POST to API
6. Click Skip → modal asking for reason → POST to API
7. After decision, job status updates (applied/skipped), button states change
8. Dashboard filter "Applied" shows all applied jobs with dates

### Components

- shadcn Dialog for decision modals
- shadcn Button with variants (primary for Apply, ghost for Skip)

## Done criteria

- [ ] Apply button writes decision to DB
- [ ] Skip button writes decision to DB
- [ ] Decision history shows on job detail
- [ ] Dashboard filter "Applied" works
- [ ] 10 existing decisions tests still pass
