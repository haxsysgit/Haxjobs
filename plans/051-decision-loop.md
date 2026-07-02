# Plan 051: Decision loop — mark applied/skipped/rejected

> **Depends on**: 048, 049, 050 | **Priority**: P1 | **Effort**: S | **Risk**: LOW
> **Planned at**: commit `bf83142`, 2026-06-30

> ⚠️ **PLANS ARE NOT FINAL** — review against current project reality before implementing.
> Every plan was drafted at a point in time. File paths, function signatures, dependency
> versions, and architecture decisions may have changed since. If the plan says
> `run_structured()` but the codebase has `run() + extract_json()`, follow the codebase.
> If the plan references a deleted file, skip that step. Use these plans as guidance,
> not gospel.

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

4. Decision buttons on JobDetailPage (from plan 050)
5. "Mark Applied" → shadcn Dialog: date applied, optional notes → POST
6. "Skip" → Dialog: reason → POST
7. After decision, button states update (applied = green, skipped = gray)
8. Dashboard filter "Applied" shows applied jobs

**shadcn components**: Dialog, Button, Input, Label

## Deliverable report (required)

After implementation, the executor must produce a compact report:

- **What changed**: files created, modified, deleted
- **Deliverables**: endpoints, pages, CLI commands the user can now use
- **How to verify**: the exact commands that prove it works
- **Deviations from plan**: what the plan said vs what was actually done
- **What was skipped**: and the reason (YAGNI, blocked, deferred)

## Done criteria

- [ ] Apply writes decision to DB
- [ ] Skip writes decision to DB
- [ ] Decision history visible on job detail
- [ ] Dashboard filter "Applied" works
- [ ] 10 existing decisions tests still pass
