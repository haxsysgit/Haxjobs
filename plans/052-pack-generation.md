# Plan 052: Pack generation — template fill, preview, download

> **Depends on**: 048, 051 | **Priority**: P2 | **Effort**: M | **Risk**: LOW
> **Planned at**: commit `bf83142`, 2026-06-30

> ⚠️ **PLANS ARE NOT FINAL** — review against current project reality before implementing.
> Every plan was drafted at a point in time. File paths, function signatures, dependency
> versions, and architecture decisions may have changed since. If the plan says
> `run_structured()` but the codebase has `run() + extract_json()`, follow the codebase.
> If the plan references a deleted file, skip that step. Use these plans as guidance,
> not gospel.

## Why this matters

The pack system exists (`packs_builder/job_pack.py`, `application_templates/`, `cv_variants/`) but is CLI-only. This plan fills `features/packs/` — generate and download packs from the job detail page.

## Steps

### Backend: features/packs/

1. **service.py**: wraps `packs_builder/job_pack.py` `build_job_pack()`
2. **routes.py**:
   - `POST /api/jobs/{id}/pack` — generates pack, returns metadata
   - `GET /api/jobs/{id}/pack/files` — file list with download URLs
   - `GET /api/jobs/{id}/pack/files/{filename}` — serves file content
   - `GET /api/jobs/{id}/pack/download` — zip download
3. **schemas.py**: `PackResponse`, `PackFileResponse`

### Frontend

4. "Generate Pack" button on job detail's Pack tab
5. File list with preview — click cover letter → inline rendered text
6. "Download All" → zip
7. Loading state while pack generates

## Deliverable report (required)

After implementation, the executor must produce a compact report:

- **What changed**: files created, modified, deleted
- **Deliverables**: endpoints, pages, CLI commands the user can now use
- **How to verify**: the exact commands that prove it works
- **Deviations from plan**: what the plan said vs what was actually done
- **What was skipped**: and the reason (YAGNI, blocked, deferred)

## Done criteria

- [ ] Pack generation works from API
- [ ] Files downloadable individually and as zip
- [ ] Cover letter preview renders in browser
- [ ] Existing pack builder tests still pass
