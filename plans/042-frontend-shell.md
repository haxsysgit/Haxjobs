# Plan 042: Frontend shell — React + Vite + shadcn/ui

> **Executor instructions**: Follow this plan step by step. Run every verification command and confirm the expected result before moving to the next step. If anything in the "STOP conditions" section occurs, stop and report — do not improvise. When done, update the status row for this plan in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat bf83142..HEAD -- dashboard/ frontend/`
> If `src/haxjobs/` doesn't exist, plan 040 must run first. If `haxjobs start` doesn't work, plan 041 must run first.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: LOW (new frontend directory, old dashboard stays until replaced)
- **Depends on**: 040, 041
- **Category**: migration
- **Planned at**: commit `bf83142`, 2026-06-30

## Why this matters

The existing `dashboard/` is an old React app built before the product pivot. We're starting fresh with Vite + React + TypeScript + shadcn/ui. shadcn/ui gives us beautiful components (tables, forms, dialogs, sidebars) out of the box — no CSS wrestling. The template at [satnaing/shadcn-admin](https://github.com/satnaing/shadcn-admin) (MIT) provides layout shell, sidebar, routing, dark mode, and data table components. We fork its structure without its demo pages.

## Current state

- `dashboard/` — old React app (will be replaced, not deleted yet)
- FastAPI server at `localhost:8241` serves `frontend/dist/` if it exists
- No `frontend/` directory yet

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Create Vite project | `npm create vite@latest frontend -- --template react-ts` | frontend/ created |
| Install deps | `cd frontend && npm install` | exit 0 |
| Add shadcn | `cd frontend && npx shadcn@latest init -d` | components.json created |
| Dev server | `cd frontend && npm run dev` | Vite on :5173 |
| Build | `cd frontend && npm run build` | frontend/dist/ created |
| Serve via FastAPI | `haxjobs start` then `curl http://localhost:8241/` | index.html |

## Scope

**In scope**:
- Delete old `dashboard/` directory
- Create `frontend/` with Vite + React + TypeScript
- Add shadcn/ui with these components: button, card, input, label, table, dialog, tabs, badge, sidebar, dropdown-menu, separator, skeleton, toast
- Add react-router-dom for routing
- Create layout shell: sidebar navigation, header, main content area
- Create placeholder pages: Dashboard, Jobs, Profile, Settings
- Build and verify FastAPI serves it

**Out of scope**:
- Real data in any page — just "Coming soon" placeholders
- Onboarding wizard UI — plan 044
- Job list/detail components — plans 047/048
- Dark mode wiring (comes free with shadcn but don't customize yet)

## Git workflow

- Commit: `git commit -m "add React + Vite + shadcn/ui frontend shell"`
- Do NOT push

## Steps

### Step 1: Delete old dashboard and create new frontend

```bash
git rm -r dashboard/
npm create vite@latest frontend -- --template react-ts
cd frontend && npm install
```

**Verify**: `ls frontend/src/App.tsx` → exists

### Step 2: Add shadcn/ui

```bash
cd frontend
npx shadcn@latest init -d
npx shadcn@latest add button card input label table dialog tabs badge sidebar dropdown-menu separator skeleton --yes
npm install react-router-dom @tanstack/react-router
```

**Verify**: `ls frontend/src/components/ui/button.tsx` → exists

### Step 3: Create layout shell

Create `frontend/src/components/layout/`. Copy the layout structure from shadcn-admin template: sidebar, header, main. Keep it minimal — sidebar with 4 nav items (Dashboard, Jobs, Profile, Settings), header with title, main area.

Key files to create:
- `src/components/layout/Sidebar.tsx` — 4 nav links
- `src/components/layout/Header.tsx` — "HaxJobs" title
- `src/components/layout/MainLayout.tsx` — sidebar + header + `<Outlet />`

### Step 4: Set up routing

In `frontend/src/main.tsx`, wrap app with BrowserRouter. Create 4 placeholder page components under `src/pages/`:
- `DashboardPage.tsx` — "Welcome to HaxJobs" card
- `JobsPage.tsx` — "Job listings coming soon"
- `ProfilePage.tsx` — "Profile settings coming soon"
- `SettingsPage.tsx` — "Settings coming soon"

### Step 5: Build and verify FastAPI serves it

```bash
cd frontend && npm run build
```

Then:
```bash
haxjobs start &
sleep 2
curl -s http://localhost:8241/ | head -c 200  # should return index.html
kill %1
```

**Verify**: curl returns HTML containing "HaxJobs" or the React root div

### Step 6: Commit

```bash
git add frontend/
git commit -m "add React + Vite + shadcn/ui frontend shell"
```

## Test plan

No automated tests for the frontend in this plan. Manual verification:
- `npm run build` exits 0
- `haxjobs start` serves the built frontend at `/`
- `/docs` still shows FastAPI auto-docs
- `/api/health` still returns `{"status":"ok"}`

## Done criteria

- [ ] Old `dashboard/` deleted
- [ ] `frontend/` exists with Vite + React + TypeScript + shadcn/ui
- [ ] `npm run build` succeeds, creates `frontend/dist/`
- [ ] `haxjobs start` serves frontend at `localhost:8241/`
- [ ] FastAPI docs at `localhost:8241/docs` still work
- [ ] Sidebar nav visible with 4 items

## STOP conditions

Stop if:

- `npx shadcn@latest init` fails — check Node.js version (needs 18+)
- `npm install` fails with peer dependency conflicts — use `--legacy-peer-deps` flag
- Frontend build takes >2 minutes — check for infinite loops in config

## Maintenance notes

- The shadcn-admin template is MIT licensed. We're using its layout patterns (sidebar structure, responsive breakpoints) but writing our own pages. No need to clone the full repo — just reference the relevant component files.
- `components.json` is created by `shadcn init` and tracked in git. It configures component paths and styling.
- The frontend is served as static files by FastAPI. In development, run the Vite dev server separately (`npm run dev`) for hot reload, and point API calls to `localhost:8241`.
