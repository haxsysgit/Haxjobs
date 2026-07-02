# Plan 054: Frontend polish — theme, responsive, navigation, empty states

> **Depends on**: 049, 050, 051, 052, 053 | **Priority**: P2 | **Effort**: M | **Risk**: LOW
> **Planned at**: commit `bf83142`, 2026-06-30

> ⚠️ **PLANS ARE NOT FINAL** — review against current project reality before implementing.
> Every plan was drafted at a point in time. File paths, function signatures, dependency
> versions, and architecture decisions may have changed since. If the plan says
> `run_structured()` but the codebase has `run() + extract_json()`, follow the codebase.
> If the plan references a deleted file, skip that step. Use these plans as guidance,
> not gospel.

## Why this matters

All pages are built but the app doesn't feel like a product. This plan adds dark mode, responsive layout, loading skeletons, empty states with CTAs, error handling, and navigation polish.

## Steps

1. **Dark mode**: wire shadcn ThemeProvider (already in shadcn init), add toggle in Header. Persist to localStorage.
2. **Responsive**: test at 375px (mobile), 768px (tablet), 1440px (desktop). Sidebar collapses to hamburger on mobile. Tables scroll horizontally. Modals go fullscreen.
3. **Loading states**: shadcn Skeleton on job list, detail, and profile pages while data fetches.
4. **Empty states**:
   - No jobs: "No jobs yet. Start a discovery run." with CTA button
   - No evaluations: "Run evaluation on pending jobs."
   - No applied jobs: "Mark jobs as applied after submitting applications."
5. **Error states**: sonner toast on fetch failure, retry button.
6. **Navigation progress bar**: thin loading bar on route changes (simple component, no extra dep — use a CSS animation triggered by router events).
7. **Favicon + title**: replace Vite defaults with HaxJobs branding.
8. **TypeScript check**: `cd frontend && npx tsc --noEmit` → clean

## Deliverable report (required)

After implementation, the executor must produce a compact report:

- **What changed**: files created, modified, deleted
- **Deliverables**: endpoints, pages, CLI commands the user can now use
- **How to verify**: the exact commands that prove it works
- **Deviations from plan**: what the plan said vs what was actually done
- **What was skipped**: and the reason (YAGNI, blocked, deferred)

## Done criteria

- [ ] Dark mode toggle works
- [ ] Mobile: sidebar collapses, tables scroll, no horizontal overflow
- [ ] Loading skeletons show during data fetches
- [ ] Empty states show helpful CTAs
- [ ] API errors show toast with retry
- [ ] `npx tsc --noEmit` → 0 errors
