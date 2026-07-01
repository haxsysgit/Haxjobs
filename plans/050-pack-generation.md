# Plan 050: Pack generation — template fill, preview, download

> **Depends on**: 048 | **Priority**: P2 | **Effort**: M | **Risk**: LOW
> **Planned at**: commit `bf83142`, 2026-06-30

## Why this matters

The pack system exists (`packs_builder/job_pack.py`, `application_templates/`, `cv_variants/`) but is CLI-only. The user should generate and download application packs from the job detail page.

## Steps

### Backend

1. `POST /api/jobs/:id/pack` — triggers pack generation using existing `build_job_pack()`, returns pack metadata
2. `GET /api/jobs/:id/pack/files` — returns list of pack files with URLs
3. `GET /api/jobs/:id/pack/files/:filename` — serves individual file content
4. `GET /api/jobs/:id/pack/download` — serves zip of all pack files
5. Wire existing `packs_builder/job_pack.py` into FastAPI route

### Frontend

6. "Generate Pack" button on job detail's Pack tab
7. File list with preview (click cover letter → shows rendered markdown)
8. "Download All" button → downloads zip
9. Loading state while pack generates

### Ponytail note

The existing `build_job_pack()` fills HTML templates with job data. Keep it. Don't rewrite the template system. Just add API endpoints around what already works.

## Done criteria

- [ ] Pack generation works from API
- [ ] Pack files downloadable individually and as zip
- [ ] Cover letter and CV preview render in browser
- [ ] Existing pack tests still pass
