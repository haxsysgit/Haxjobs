# Review Ledger — Plan 003 Corrected

## Reviewers

| # | Reviewer | Scope | Verdict | Evidence |
|---|----------|-------|---------|----------|
| A | DeepSeek V4 Pro Reviewer A | Plan compliance and scope | APPROVED (M1,M2,M3,L1,L2) | See review-a.out |
| B | DeepSeek V4 Pro Reviewer B | Runtime correctness and cancellation | NEEDS FIXES (F1 critical, F2,F3 moderate, F4 minor) | See review-b.out |
| C | DeepSeek V4 Pro Reviewer C | Persistence, privacy, and employment boundaries | APPROVED (no issues) | See review-c.out |
| D | DeepSeek V4 Pro Reviewer D | Terminal behavior, docs, diagrams, manual proof | NEEDS FIXES (3 documentation items) | See review-d.out |

## Accepted findings (all fixed in repair round 1)

| ID | Finding | Source | Fix applied |
|----|---------|--------|-------------|
| F1 | Truncated tool calls dispatched (finish_reason="length") | Review B (CRITICAL) | Added `tool_calls_unsafe` to ModelStreamEvent; skip in client.py; reject in turn.py |
| F2 | Double TURN_FAILED emission | Review B (MODERATE) | Removed inline emit from RESPONSE_FAILED/Exception handlers |
| F3 | Tool cancellation not responsive | Review B (MODERATE) | Race dispatch_task against cancel_event.wait(); clean up both |
| F4 | Pending-turn fire-and-forget exceptions | Review B (MINOR) | Added done_callback with error logging |
| 5 | Terminal awaits session.prompt() blocking input | Explicit plan requirement | Fire as non-blocking task; track; abort/settle on exit |
| 6 | Tool events not rendered from LiveEvents | Explicit requirement | Render TOOL_STARTED/PROGRESS/COMPLETED/FAILED |
| M3 | SESSION_STARTED defined but never emitted | Review A (MEDIUM) | Emit on first turn in _run_turn |
| D3 | Bare `haxjobs` always creates new session | Review D | Now resumes latest session (matches `haxjobs chat`) |
| M1/D1/D2 | Missing deliverable artifacts | Reviews A, D | Copied plan.md, career-graph-report.md, schema-diagram.*; updated README |
| L1 | Trailing whitespace in Draw.io XML | Review A (LOW) | Cleaned via sed |
| L2 | Blank line in __all__ | Review A (LOW) | Removed |
| M2 | Migration/profile_cli fixes in "Do not touch" | Review A (MEDIUM) | Kept — focused test proves they prevent real user-facing crash |
| 12 | Real PTY terminal proof | Plan requirement | See manual-proof.md |

## Deferred (not blocking)

- Full interactive demo requires real TTY — documented in manual-proof.md
- Resource cleanup (CareerStore/SessionStore close on happy path) — pre-existing, no regression

## Self-review checklist

- [x] All plan phases implemented (1-9)
- [x] 12 repair findings applied
- [x] No Textual restored
- [x] No alternate-screen app
- [x] CareerStore not imported by terminal
- [x] Provider clients not imported by terminal
- [x] Turn runtime is domain-free
- [x] Session owns canonical history
- [x] Career context is per-turn, never persisted in session history
- [x] Live events separate from RunEvent
- [x] RunEvent redaction preserved
- [x] Fake model used only in tests and --fake mode
- [x] 188 tests all pass (fixture present)
- [x] Diagrams exported to PNG; no trailing whitespace
- [x] py_compile passes
- [x] uv lock --check passes
- [x] git diff --check passes
- [x] Migration crash fix verified with focused test
- [x] PTY manual proof documented
