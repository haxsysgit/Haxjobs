# Plan 046: Onboarding frontend — multi-step wizard UI

> **Depends on**: 056, 043 | **Priority**: P1 | **Effort**: M | **Risk**: LOW
> **Planned at**: commit `bf83142`, 2026-06-30

## Why this matters

The onboarding backend (043) has endpoints. This plan builds the wizard UI: file upload with drag-and-drop, progress during extraction, step-by-step questions, profile preview. First thing a new user sees.

## Steps

1. Create `frontend/src/pages/OnboardingPage.tsx` with multi-step component
2. Step 1: CV upload — drag-and-drop zone using native `<input type="file">` with styled drop area (no extra dep)
3. Step 2: Extraction progress — spinner + status text while LLM processes (use `useMutation` from @tanstack/react-query)
4. Step 3: Wizard questions — one at a time, text/select/multi-select inputs using shadcn Form + react-hook-form
5. Step 4: Profile preview — show extracted data in shadcn Cards, "Looks good" / "Edit" buttons
6. Step 5: Save — `POST /api/onboarding/complete`, redirect to Dashboard
7. Route: `/onboarding` shows this page if no profile exists (check `GET /api/profile`), else redirect to `/`

**shadcn components used**: Card, Button, Input, Label, Select, Checkbox, Textarea, Badge, Separator, Form (react-hook-form integration)

**Verify**: Upload CV → extraction completes → wizard shows questions → profile preview → save → redirect

## Done criteria

- [ ] Drag-and-drop upload works
- [ ] Extraction progress shows during LLM call
- [ ] Wizard steps flow logically without page reload
- [ ] Profile preview shows all extracted fields
- [ ] Save writes and redirects

## STOP conditions

- File >10MB — add size validation
- LLM >60s — add timeout + retry UI
- PDF parsing fails on scanned docs — show "paste text" fallback
