# Plan 004: Enforce approval state transitions

> **Executor instructions**: Follow this plan step by step. Run every verification command and confirm expected results. If a STOP condition occurs, stop and report.
>
> **Drift check (run first)**: `git diff --stat b725a33..HEAD -- db/pack_review.py db/outreach.py server/routes/outreach.py server/routes/jobs.py tests`

## Status

- **Priority**: P1
- **Effort**: S/M
- **Risk**: LOW
- **Depends on**: plans/001-restore-verification-baseline.md
- **Category**: correctness
- **Planned at**: commit `b725a33`, 2026-06-27

## Why this matters

HaxJobs relies on approval checkpoints. Today, outreach draft approval/rejection can report success for a draft ID that does not exist, and pack review can approve/reject/change-request a job even when no pack has been generated. That creates false approval history and weakens the safety boundary around outreach and application materials.

## Current state

Relevant files:
- `db/outreach.py` — update draft status helper.
- `server/routes/outreach.py` — dashboard/API approve and reject endpoints.
- `db/pack_review.py` — pack review state transitions.
- `server/routes/jobs.py` — `review_job_pack` API route.
- `tests/test_pack_review_gate.py` — existing pack review tests.

Current excerpts:
- `db/outreach.py:125-138`: `update_draft_status()` runs `UPDATE outreach_drafts SET status=? WHERE id=?`, commits, and returns nothing.
- `server/routes/outreach.py:136-151`: approve/reject return `{"ok": True}` if no exception is raised.
- `db/pack_review.py:37-41`: validates only that the job exists.
- `db/pack_review.py:43-54`: updates `pack_status` and records a decision regardless of previous `pack_status`.
- `tests/test_pack_review_gate.py` already tests valid review actions but not missing pack/generated state preconditions.

Repo conventions:
- Use direct DB helper tests with temp SQLite DB monkeypatches as in `tests/test_manual_pack_generation.py`.
- Keep API payloads simple: `ok`, `error`, IDs/status fields.

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| Pack review tests | `python3 -m pytest tests/test_pack_review_gate.py -q` | exit 0 |
| Outreach tests | `python3 -m pytest tests/test_outreach_review.py -q` | exit 0 |
| Full tests | `python3 -m pytest -q` | exit 0 |
| Python syntax | `python3 -m py_compile $(find . -path './dashboard/node_modules' -prune -o -path './.git' -prune -o -path './.venv' -prune -o -name '*.py' -print)` | exit 0 |

## Scope

In scope:
- `db/outreach.py`
- `server/routes/outreach.py`
- `db/pack_review.py`
- `server/routes/jobs.py` only if route status mapping needs adjustment
- Tests under `tests/`

Out of scope:
- Adding new first-class ApprovalCheckpoint tables. This is future work.
- Sending or approving actual LinkedIn messages.
- Changing draft generation templates.

## Git workflow

- Branch suggestion: `advisor/004-enforce-approval-transitions`

## Steps

### Step 1: Make outreach draft status updates report row existence

Change `db.outreach.update_draft_status(draft_id, status)` to return a structured result or boolean. It should indicate false/not found when `cursor.rowcount == 0`. Preserve `sent_at=datetime('now')` behavior for `status == "sent"`.

Update `server/routes/outreach.py`:
- Approve/reject a missing draft should return `{"ok": false, "error": "draft not found"}` and a 404 if route plumbing supports status codes, or at minimum `ok: false`.
- Existing dashboard code already checks `r.ok`, so keep that contract.

Add tests for approving and rejecting a missing draft.

Verify: `python3 -m pytest tests/test_outreach_review.py -q` → exit 0.

### Step 2: Restrict pack review to generated or review-change states

In `db.pack_review.review_pack`, fetch current `pack_status` as well as `id`. Allow review actions only when current status means a pack exists and is reviewable, such as `generated` or `review_changes_requested` if that is intended. Reject `none`, empty, missing, skipped, or already final-reviewed states with a clear error.

Add tests:
- A job with `pack_status='none'` cannot be approved.
- A generated pack can still be approved/rejected/changes.
- A missing job still returns `job not found`.

Verify: `python3 -m pytest tests/test_pack_review_gate.py -q` → exit 0.

### Step 3: Keep decision logging aligned

Ensure `record_decision()` only runs after a real pack review transition succeeds. Missing draft updates do not need decision logging unless a decision table is explicitly used for outreach later.

Verify: add assertions where cheap, then run full tests.

## Test plan

- Extend `tests/test_pack_review_gate.py` for invalid pack state.
- Add `tests/test_outreach_review.py` or extend an existing outreach test file for missing draft approve/reject.
- Use temp DB monkeypatches; do not touch live `/home/hermes/haxjobs/state/pipeline.db`.

## Done criteria

- [ ] Missing outreach draft approval/rejection returns `ok: false`.
- [ ] Pack review rejects jobs without generated/reviewable packs.
- [ ] Valid generated-pack review paths still pass.
- [ ] Decision log is written only for successful pack review transitions.
- [ ] Focused tests pass.
- [ ] `python3 -m pytest -q` exits 0.
- [ ] Python compile command exits 0.
- [ ] `plans/README.md` row 004 updated when done.

## STOP conditions

Stop and report if:
- Existing dashboard expects HTTP 200 for all failed approvals and cannot handle non-200 responses.
- Current production DB has pack statuses beyond those visible in code and the allowed set is unclear.

## Maintenance notes

This plan is a bridge toward first-class approval checkpoint records. Future work should add an append-only approval table, but this plan must keep current fields safe first.
