# Plan 049: Decision loop — mark applied/skipped/rejected

> **Depends on**: 048 | **Priority**: P1 | **Effort**: S | **Risk**: LOW
> **Planned at**: commit `bf83142`, 2026-06-30

## Why this matters

The `decisions` table already exists in DB schema with `db/decisions.py` functions and 10 passing tests. Nothing calls them from API/UI. This plan closes the feedback loop.

## Steps

### Backend: features/decisions/

1. **routes.py**:
   - `POST /api/jobs/{id}/decision` — body: `{decision: "applied"|"skipped"|"rejected", notes: "..."}`
   - `GET /api/jobs/{id}/decisions` — decision history
2. **service.py**: thin wrapper over `db/decisions.py` functions
3. **schemas.py**: `DecisionRequest`, `DecisionResponse`

### Frontend

4. Decision buttons on JobDetailPage (already from plan 048)
5. "Mark Applied" → shadcn Dialog: date applied, optional notes → POST
6. "Skip" → Dialog: reason → POST
7. After decision, button states update (applied = green, skipped = gray)
8. Dashboard filter "Applied" shows applied jobs

**shadcn components**: Dialog, Button, Input, Label

## Done criteria

- [ ] Apply writes decision to DB
- [ ] Skip writes decision to DB
- [ ] Decision history visible on job detail
- [ ] Dashboard filter "Applied" works
- [ ] 10 existing decisions tests still pass
