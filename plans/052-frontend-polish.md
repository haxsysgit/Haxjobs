# Plan 052: Frontend polish — theme, responsive, navigation, empty states

> **Depends on**: 042, 047 | **Priority**: P2 | **Effort**: M | **Risk**: LOW
> **Planned at**: commit `bf83142`, 2026-06-30

## Why this matters

All the pages are built but the app doesn't feel like a product yet. This plan adds: dark mode, responsive layout for mobile, smooth page transitions, loading skeletons, empty states with helpful messaging, error boundaries, and consistent spacing/typography.

## Steps

1. **Dark mode**: wire shadcn theme provider, add toggle in header. Persist preference to localStorage.
2. **Responsive**: test all pages at 375px (mobile), 768px (tablet), 1440px (desktop). Fix layout breaks — sidebar collapsible on mobile, tables scroll horizontally, modals fullscreen on mobile.
3. **Loading states**: add shadcn Skeleton components to job list, detail, and profile pages while data loads.
4. **Empty states**: when no jobs discovered → "No jobs yet. Start a discovery run to find jobs matching your profile." with CTA button. When no evaluations → "Run evaluation on pending jobs to see fit scores."
5. **Error states**: API error toast on fetch failure, retry button.
6. **Navigation progress bar**: show loading indicator on route changes.
7. **Favicon + page title**: update from default Vite.

## Done criteria

- [ ] Dark mode toggle works
- [ ] Mobile layout doesn't break (sidebar collapses, tables scroll)
- [ ] Loading skeletons show while data loads
- [ ] Empty states show helpful CTAs
- [ ] API errors show toast with retry
