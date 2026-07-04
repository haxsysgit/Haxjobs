# HaxJobs frontend

React + TypeScript + Vite UI for the local HaxJobs FastAPI app.

## Commands

```bash
npm ci
npx tsc --noEmit
npm run build
npm run lint -- --quiet
npm run dev
```

The normal app is served by the Python backend at `localhost:8241` after `npm run build`. Use Vite dev mode only for frontend-only work; API calls are relative `/api` requests and expect a backend to be available.

## Structure

- `src/App.tsx` sets up React Router.
- `src/pages/` contains page-level flows like setup, onboarding, discovery, jobs, and profile.
- `src/components/layout/` contains the sidebar, header, and route guard.
- `src/components/ui/` contains local shadcn-style primitives.
