# Plan 001: Restore the verification baseline

> **Executor instructions**: Follow this plan step by step. Run every verification command and confirm the expected result before moving to the next step. If any STOP condition occurs, stop and report instead of improvising.
>
> **Drift check (run first)**: `git diff --stat b725a33..HEAD -- application_templates dashboard tests README.md`
> If any in-scope file changed since this plan was written, compare the Current state excerpts below against live code before proceeding.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: tests / dx
- **Planned at**: commit `b725a33`, 2026-06-27

## Why this matters

The current repo has useful tests, but the verification baseline is red. Python tests fail because the current uncommitted cover-letter template changes include an em dash. Dashboard typecheck also fails on unused imports, and lint reports many errors. Cleanup/security plans should not start until a failing command means “new regression”, not “known old noise”.

## Current state

Relevant files:
- `application_templates/cover_letters/ai_automation_agents.md` — currently contains an em dash in governance prose.
- `tests/test_application_templates.py` — rejects em dashes in templates.
- `dashboard/src/pages/Outreach.tsx` — imports unused icons.
- `dashboard/src/data/api.ts` and dashboard pages — contain `any` and lint violations.
- `README.md` — lists checks but does not include `pytest`.

Current excerpts:
- `application_templates/cover_letters/ai_automation_agents.md:3`: `VOICE: Arinze — confident, grounded, shows don't tells...`
- `tests/test_application_templates.py:55`: asserts templates contain no em dash.
- `dashboard/src/pages/Outreach.tsx:2`: imports `Send, Mail, Clock, CheckCircle, X, FileText, ExternalLink`; `Mail` and `Clock` are unused.
- `dashboard/tsconfig.app.json:18-20`: `noUnusedLocals` and `noUnusedParameters` are true.
- `README.md:57-65`: check block lacks `python3 -m pytest -q`.

Repo conventions:
- Use `python3`, not `python`.
- The existing Python test suite uses pytest and temporary SQLite DB monkeypatches. Match patterns in `tests/test_manual_pack_generation.py` and `tests/test_pack_detail_api.py`.
- Dashboard code is React + TypeScript + Vite. Keep simple explicit types, no cryptic one-liners.

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| Python tests | `python3 -m pytest -q` | exit 0, all tests pass |
| Python syntax | `python3 -m py_compile $(find . -path './dashboard/node_modules' -prune -o -path './.git' -prune -o -path './.venv' -prune -o -name '*.py' -print)` | exit 0 |
| Shell syntax | `bash -n cron/run_pipeline.sh scripts/haxjobs-update dashctl.sh build-dash.sh dev-watch.sh pack_builder.sh` | exit 0 |
| Dashboard typecheck | `cd dashboard && npx tsc -b --noEmit` | exit 0 |
| Dashboard lint | `cd dashboard && npm run lint -- --quiet` | exit 0 |
| Dashboard build | `cd dashboard && npm run build` | exit 0 |

## Scope

In scope:
- `application_templates/cover_letters/*.md`
- `dashboard/src/**/*.tsx`
- `dashboard/src/**/*.ts`
- `README.md`
- Existing tests only if they are stale relative to intended rules

Out of scope:
- Runtime directories: `intake/`, `packs/`, `state/`, `reports/`, `outreach/`
- Changing template meaning beyond removing forbidden punctuation/style drift
- Disabling lint rules globally just to make errors disappear
- Installing new dashboard test frameworks. That is Plan 008/other future work, not this baseline fix.

## Git workflow

- Branch suggestion: `advisor/001-restore-verification-baseline`
- Commit style in repo history is imperative, e.g. `Fix Outreach dashboard — XCircle to X icon`.
- Do not push unless the operator asks.

## Steps

### Step 1: Fix the Python test failure from template punctuation

Replace em dashes in modified cover-letter templates with commas, periods, colons, or parentheses. Do not change the “No em dashes” rule. Search all application template markdown files, not just the failing one.

Verify: `python3 -m pytest tests/test_application_templates.py -q` → exit 0.

### Step 2: Make dashboard typecheck pass

Remove unused imports/variables first. In particular, remove unused `Mail` and `Clock` from `dashboard/src/pages/Outreach.tsx`. Fix any remaining `tsc` errors without weakening `tsconfig.app.json`.

Verify: `cd dashboard && npx tsc -b --noEmit` → exit 0.

### Step 3: Make dashboard lint pass without hiding real problems

Address lint errors in small groups:
- Replace `any` with existing or new explicit response types in `dashboard/src/data/api.ts`.
- For unused caught errors, either omit the binding with `catch { ... }` or use the error meaningfully.
- For React refresh warnings, move exported non-component helpers/constants into a separate file, or disable the rule only if the repo already uses that local pattern. Prefer moving shared helpers.
- For React hooks `set-state-in-effect` warnings, either derive state directly or restructure effects so the state update is not the first synchronous action. Do not introduce behavior changes to approval/pack flows.

Verify: `cd dashboard && npm run lint -- --quiet` → exit 0.

### Step 4: Add the existing Python tests to documented checks

Update `README.md` so the Checks section includes `python3 -m pytest -q`. Preserve the existing compile, shell syntax, and dashboard build commands. If you add a helper script instead, keep README and script consistent.

Verify: read `README.md` and confirm `python3 -m pytest -q` appears in the Checks block.

### Step 5: Run the full baseline

Run all commands from “Commands you will need”. Fix only issues introduced by this plan or obvious baseline issues in scope.

## Test plan

No new tests are required unless an existing test is stale. The core deliverable is green baseline commands.

## Done criteria

- [ ] `python3 -m pytest -q` exits 0.
- [ ] Python compile command exits 0.
- [ ] `bash -n ...` exits 0.
- [ ] `cd dashboard && npx tsc -b --noEmit` exits 0.
- [ ] `cd dashboard && npm run lint -- --quiet` exits 0.
- [ ] `cd dashboard && npm run build` exits 0.
- [ ] README Checks include the pytest command.
- [ ] No runtime/private files are modified.
- [ ] `plans/README.md` row 001 updated when done.

## STOP conditions

Stop and report if:
- Dashboard lint requires a broad config downgrade to pass.
- Fixing hook lint requires redesigning Pipeline or Profile behavior beyond mechanical cleanup.
- Python tests fail for reasons unrelated to templates or current modified files.

## Maintenance notes

Future cleanup plans assume this baseline is green. Reviewers should reject broad “disable lint” fixes unless there is a very explicit rationale.
