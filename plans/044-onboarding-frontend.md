# Plan 044: Onboarding frontend — multi-step wizard UI

> **Depends on**: 042, 043 | **Priority**: P1 | **Effort**: M | **Risk**: LOW
> **Planned at**: commit `bf83142`, 2026-06-30

## Why this matters

The onboarding backend (043) has endpoints. This plan builds the wizard UI: file upload with drag-and-drop, progress bar during extraction, step-by-step questions with smooth transitions, profile preview before saving. First thing a new user sees — sets the tone for the whole product.

## Steps

1. Create `frontend/src/pages/OnboardingPage.tsx` with multi-step component
2. Step 1: CV upload — drag-and-drop zone, file preview, "Extract" button
3. Step 2: Extraction progress — spinner + status text while LLM processes
4. Step 3: Wizard questions — one question at a time, text/select/multi-select inputs
5. Step 4: Profile preview — show extracted data, "Looks good" / "Edit" buttons
6. Step 5: Save — write to backend, redirect to Dashboard
7. Route: `/onboarding` shows this page if no profile exists, otherwise redirect

**Components to reuse from shadcn/ui**: Card, Button, Input, Label, Select, Checkbox, Progress, Badge, Separator

**Verify**: Upload a CV PDF → extraction completes → wizard shows questions → profile preview → save → redirect to dashboard

## Done criteria

- [ ] Drag-and-drop upload works
- [ ] Extraction progress shows during LLM call
- [ ] Wizard steps flow logically without page reload
- [ ] Profile preview shows all extracted fields
- [ ] Save writes to backend and redirects

## STOP conditions

- File upload exceeds 10MB — add size validation
- LLM extraction takes >60s — add timeout + retry UI
- PDF parsing fails on scanned documents — show "plain text paste" fallback
