# Plan 042: Frontend shell — React + Vite + shadcn/ui (minimal deps)

> **Executor instructions**: Follow this plan step by step. Run every verification command and confirm the expected result before moving to the next step. If anything in the "STOP conditions" section occurs, stop and report — do not improvise. When done, update the status row for this plan in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat bf83142..HEAD -- dashboard/ frontend/`
> If `src/haxjobs/app.py` doesn't exist, plan 041 must run first.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: LOW (new frontend directory, old dashboard deleted)
- **Depends on**: 040, 041
- **Category**: migration
- **Planned at**: commit `bf83142`, 2026-06-30

## Why this matters

The existing `dashboard/` is an old React app built before the product pivot. We start fresh with Vite + React + TypeScript + shadcn/ui. We do NOT fork the shadcn-admin template — it brings 30+ dependencies we don't need (Clerk auth, recharts, date-fns, cmdk, input-otp, zustand, faker, playwright, knip). Instead we scaffold clean and add only what the product needs.

## Dependencies — what we keep vs strip

shadcn-admin has 35 runtime deps. HaxJobs needs 10:

| Keep (essential) | Strip (not needed for HaxJobs) |
|---|---|
| react, react-dom | `@clerk/react` — auth, HaxJobs has no auth |
| @tanstack/react-query | `recharts` — charts, not in v1 |
| @tanstack/react-router | `date-fns` — use native Intl.RelativeTimeFormat |
| @tanstack/react-table | `cmdk` — command palette, nice but not v1 |
| lucide-react | `input-otp` — auth feature |
| react-hook-form + @hookform/resolvers | `zustand` — React Query handles server state |
| sonner (toasts) | `react-top-loading-bar` — cosmetic |
| class-variance-authority | `react-day-picker` — date picker, not in v1 |
| clsx + tailwind-merge | `axios` — use native fetch |

Radix UI primitives come via shadcn/ui components, not direct deps. Only add the shadcn components we actually use.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Create Vite | `npm create vite@latest frontend -- --template react-ts` | frontend/ created |
| Install deps | `cd frontend && npm install` | exit 0 |
| Add shadcn | `cd frontend && npx shadcn@latest init -d` | components.json created |
| Add components | `cd frontend && npx shadcn@latest add button card ...` | components/ui/ populated |
| Dev server | `cd frontend && npm run dev` | Vite on :5173 |
| Build | `cd frontend && npm run build` | frontend/dist/ created |
| Serve via FastAPI | `uv run haxjobs start --no-browser` then `curl localhost:8241/` | index.html |

## Scope

**In scope**:
- Delete old `dashboard/` directory
- Create `frontend/` with Vite + React + TypeScript
- Add ONLY these shadcn components: button, card, input, label, badge, table, dialog, tabs, dropdown-menu, separator, skeleton, sidebar, select, checkbox, textarea, toast (sonner)
- Add: react-hook-form, @hookform/resolvers, @tanstack/react-query, @tanstack/react-router, @tanstack/react-table
- Create layout shell: sidebar nav, header, main content area with Outlet
- Create placeholder pages: Dashboard, Jobs, Profile, Setup
- Build and verify FastAPI serves it at `/`

**Out of scope**:
- Forking shadcn-admin template — we build our own layout
- Clerk, recharts, date-fns, cmdk, zustand, react-top-loading-bar, react-day-picker, axios — none added
- SetupPage full implementation — that's plan 044
- Real data in any page — "Coming soon" placeholders
- Onboarding wizard UI — plan 046
- Job list/detail components — plans 047/048

## Git workflow

- Commit: `git commit -m "add React + Vite + shadcn/ui frontend shell"`
- Do NOT push

## Steps

### Step 1: Delete old dashboard, scaffold new frontend

```bash
git rm -r dashboard/
npm create vite@latest frontend -- --template react-ts
cd frontend && npm install
```

**Verify**: `ls frontend/src/App.tsx` → exists. `ls dashboard/ 2>/dev/null` → does not exist.

### Step 2: Install only the deps we need

```bash
cd frontend
npm install react-hook-form @hookform/resolvers
npm install @tanstack/react-query @tanstack/react-router @tanstack/react-table
npm install sonner
```

**Verify**: `grep -E "clerk|recharts|date-fns|cmdk|zustand|axios|input-otp|react-day-picker|react-top-loading-bar" frontend/package.json` → no matches (none of these should appear)

### Step 3: Add shadcn/ui

```bash
cd frontend
npx shadcn@latest init -d
npx shadcn@latest add button card input label badge table dialog tabs dropdown-menu separator skeleton sidebar select checkbox textarea --yes
npm install sonner
npx shadcn@latest add sonner --yes
```

**Verify**: `ls frontend/src/components/ui/button.tsx frontend/src/components/ui/sidebar.tsx frontend/src/components/ui/card.tsx` → all three exist

### Step 4: Create layout shell

Create the layout structure from scratch (NOT copied from shadcn-admin):

```
frontend/src/
  main.tsx                  — BrowserRouter + QueryClient + ThemeProvider
  App.tsx                   — route definitions
  components/
    layout/
      MainLayout.tsx        — sidebar + header + <Outlet />
      Sidebar.tsx           — nav links using shadcn Sidebar component
      Header.tsx            — "HaxJobs" title + theme toggle
  pages/
    DashboardPage.tsx       — "Welcome to HaxJobs" card
    JobsPage.tsx            — "Job listings coming soon"
    ProfilePage.tsx         — "Profile settings coming soon"
  lib/
    utils.ts                — cn() utility from shadcn
```

`MainLayout.tsx`:
```tsx
import { Outlet } from "@tanstack/react-router"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"
import { AppSidebar } from "./Sidebar"
import { Header } from "./Header"

export function MainLayout() {
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <Header />
        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}
```

`Sidebar.tsx`:
```tsx
import { Link } from "@tanstack/react-router"
import {
  Sidebar, SidebarContent, SidebarGroup, SidebarGroupContent,
  SidebarMenu, SidebarMenuButton, SidebarMenuItem,
} from "@/components/ui/sidebar"
import { LayoutDashboard, Briefcase, User } from "lucide-react"

const items = [
  { title: "Dashboard", url: "/", icon: LayoutDashboard },
  { title: "Jobs", url: "/jobs", icon: Briefcase },
  { title: "Profile", url: "/profile", icon: User },
]

export function AppSidebar() {
  return (
    <Sidebar>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {items.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild>
                    <Link to={item.url}>
                      <item.icon />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  )
}
```

**Verify**: `cd frontend && npx tsc -b --noEmit` → no type errors

### Step 5: Build and verify FastAPI serves it

```bash
cd frontend && npm run build
```

Then:
```bash
uv run haxjobs start --no-browser &
sleep 2
curl -s http://localhost:8241/ | head -c 200  # should return index.html
kill %1
```

**Verify**: curl returns HTML containing `<div id="root">`

### Step 6: Commit

```bash
git add frontend/ pyproject.toml
git commit -m "add React + Vite + shadcn/ui frontend shell, delete old dashboard"
```

## Test plan

No automated tests for frontend in this plan. Manual:
- `npm run build` exits 0
- `npm run dev` opens Vite on :5173
- `uv run haxjobs start` serves frontend at `/`
- API docs at `/docs` still work
- `/api/health` still returns `{"status":"ok"}`
- Sidebar has 3 nav items: Dashboard, Jobs, Profile. Setup page shown on first visit if no provider configured.

## Done criteria

- [ ] Old `dashboard/` deleted
- [ ] `frontend/` exists with Vite + React + TypeScript + shadcn/ui
- [ ] No Clerk, recharts, date-fns, cmdk, zustand, input-otp, react-day-picker, react-top-loading-bar, axios in deps
- [ ] `npm run build` succeeds
- [ ] `uv run haxjobs start` serves frontend at `localhost:8241/`
- [ ] FastAPI docs at `localhost:8241/docs` still work
- [ ] Sidebar nav visible with 3 items
- [ ] `npx tsc -b --noEmit` passes

## STOP conditions

Stop if:

- `npx shadcn@latest init` fails — check Node.js version (needs 18+)
- `npm install` fails with peer dependency conflicts — use `--legacy-peer-deps`
- TypeScript errors in layout components — check shadcn component imports match the actual component names
- Frontend build doesn't serve from FastAPI — check `_FRONTEND_DIR` path in `app.py` points to `../frontend/dist/` relative to `src/haxjobs/app.py`

## Maintenance notes

- shadcn components are copied into `src/components/ui/`, not node_modules. They're ours to modify.
- The `cn()` utility in `lib/utils.ts` is the standard shadcn pattern: `export function cn(...inputs: ClassValue[]) { return twMerge(clsx(inputs)) }`
- Routing uses `@tanstack/react-router` file-based routing. Placeholder routes for now, real routes in plans 043-052.
- When adding new shadcn components later, run `npx shadcn@latest add <name> --yes` from the frontend directory.
