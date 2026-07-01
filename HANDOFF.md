# Handoff

**Plans 038, 040, 041, 042 are DONE.** Commits: `6d65912` (040), `6929976` (041), `17e25af` (042), `72b15ff` (mark).

- 038: README shows "Under construction" warning
- 040: Repo restructured as `uv` + `hatchling` package under `src/haxjobs/`
- 041: FastAPI backend — feature-based structure, 7 feature modules, 9 API paths
- 042: Frontend shell — Vite + React 19 + TypeScript + shadcn/ui v4, sidebar layout, 4 routes

**42/44 were swapped** — frontend shell runs before provider setup (UI needs to exist first).

```
uv run haxjobs start   →  http://localhost:8241   (API + frontend)
cd frontend && npm run dev  →  http://localhost:5173  (dev with HMR)
```

Frontend: Dashboard, Jobs, Setup, Profile — all placeholder pages. shadcn sidebar layout with `react-router-dom`. 255 tests pass.

**Deviations from plan 042:**
- `react-router-dom` instead of `@tanstack/react-router` (plan's code patterns match react-router-dom exactly, tanstack needs file-based routing setup)
- shadcn v4 `render` prop instead of v3 `asChild` (breaking API change)
- 8 shadcn components instead of 17 (only what the shell actually uses)
- `npx tsc --noEmit` instead of `npx tsc -b --noEmit` (Vite template doesn't use project references)

**Next: Plan 044** — Provider setup (backend API + frontend SetupPage).

**Working dir:** `/home/hax/haxjobs`
