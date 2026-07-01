# Plan 051: Profile settings — view and edit profile

> **Depends on**: 043 | **Priority**: P2 | **Effort**: M | **Risk**: LOW
> **Planned at**: commit `bf83142`, 2026-06-30

## Why this matters

After onboarding, users need to update their profile: new skills, changed preferences, updated work authorization. The profile is the backbone of evaluation — stale profile = bad job matches. This plan makes the profile editable through the UI, not by hunting for a JSON file.

## Steps

### Backend

1. `GET /api/profile` — returns the full profile JSON
2. `PUT /api/profile` — saves updated profile
3. `PATCH /api/profile` — merges partial updates
4. Validate against profile schema on save (basic: required fields present, types correct)

### Frontend

5. Replace `ProfilePage.tsx` placeholder with editable form:
   - **Basic info**: name, email, phone, location, work authorization (read-only from extraction, but editable)
   - **Skills**: tag input — add/remove skills with autocomplete
   - **Work experience**: list of roles with inline edit (title, company, dates, bullets)
   - **Education**: list with inline edit
   - **Projects**: list with inline edit
   - **Preferences**: role types (checkboxes), preferred locations (multi-select), salary range, work modes, excluded companies
6. Save button → PUT to API
7. Confirmation toast on success

### Components

- shadcn Form + Input for text fields
- shadcn Select for dropdowns
- shadcn Checkbox group for role types
- shadcn Badge with X for tag-style skill list
- shadcn Toast for save confirmation

## Done criteria

- [ ] Profile loads from API and displays
- [ ] All fields editable
- [ ] Save persists to `~/.haxjobs/profile.json`
- [ ] Validation rejects invalid data (e.g., empty name)
