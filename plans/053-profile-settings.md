# Plan 053: Profile settings — view and edit profile

> **Depends on**: 045, 042 | **Priority**: P2 | **Effort**: M | **Risk**: LOW
> **Planned at**: commit `bf83142`, 2026-06-30

> ⚠️ **PLANS ARE NOT FINAL** — review against current project reality before implementing.
> Every plan was drafted at a point in time. File paths, function signatures, dependency
> versions, and architecture decisions may have changed since. If the plan says
> `run_structured()` but the codebase has `run() + extract_json()`, follow the codebase.
> If the plan references a deleted file, skip that step. Use these plans as guidance,
> not gospel.

## Why this matters

After onboarding, users need to update their profile. Stale profile = bad job matches. This plan fills `features/profile/` — view and edit via the UI.

## Steps

### Backend: features/profile/

1. **service.py**:
   - `get_profile() -> dict` — loads from `~/.haxjobs/profile.json`
   - `update_profile(data: dict) -> dict` — merges + validates + saves
2. **routes.py**:
   - `GET /api/profile` — full profile
   - `PUT /api/profile` — full replace
   - `PATCH /api/profile` — partial update
3. **schemas.py**: `ProfileResponse`, `ProfileUpdate`

### Frontend: ProfilePage

Replace placeholder with form:
- **Basic info**: name, email, phone, location, work authorization (editable)
- **Skills**: tag input — add/remove with autocomplete (use state array + badges with X)
- **Work experience**: list of cards with inline edit
- **Education**: list with inline edit
- **Projects**: list with inline edit
- **Preferences**: checkboxes for role types, multi-select for locations, inputs for salary/work modes/exclusions

**shadcn components**: Form (react-hook-form), Input, Select, Checkbox, Badge, Button, Card, Separator, Toast (sonner)

## Deliverable report (required)

After implementation, the executor must produce a compact report:

- **What changed**: files created, modified, deleted
- **Deliverables**: endpoints, pages, CLI commands the user can now use
- **How to verify**: the exact commands that prove it works
- **Deviations from plan**: what the plan said vs what was actually done
- **What was skipped**: and the reason (YAGNI, blocked, deferred)

## Done criteria

- [ ] Profile loads from API and displays
- [ ] All sections editable
- [ ] Save persists to `~/.haxjobs/profile.json`
- [ ] Validation rejects empty name / invalid email
