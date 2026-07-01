# Plan 050: Pack generation — template fill, preview, download

> **Depends on**: 048 | **Priority**: P2 | **Effort**: M | **Risk**: LOW
> **Planned at**: commit `bf83142`, 2026-06-30

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

## Done criteria

- [ ] Pack generation works from API
- [ ] Files downloadable individually and as zip
- [ ] Cover letter preview renders in browser
- [ ] Existing pack builder tests still pass
