# Plan 004 Review Ledger

## Status

Final review is pending and not approved. This focused writer pass starts at `65dd9d6` and makes one correctness/truthfulness repair commit. No live model, public network, private fixture, provider configuration, credential, plan, or state path was used.

## Prior review history

| Candidate | Outcome | Scope |
|---|---|---|
| `0cbff2b` | rejected | Initial Plan 004 implementation; PTY isolation, PNG exports, and report metadata blockers |
| `0766d56` | accepted with blockers | Isolated PTY tests, exported diagrams, corrected deliverable metadata |
| `65dd9d6` | blocked by three fresh Luna reviews | Mandatory session configuration, tool-event ordering, and assessment/source/cancellation truthfulness defects |

## Repairs in this commit

1. SessionStore creation now requires a nonblank valid JSON object and validates before inserting the session. Historic unconfigured rows are still rejected clearly on resume; they are not repaired.
2. Tool results are persisted before `TOOL_COMPLETED`/`TOOL_FAILED`. Result persistence failure emits persistence failure/terminal events, stops before another model call, and leaves the call eligible for dangling-call reconciliation.
3. `JobSourceFetcher.fetch(JobFixture, ...)` and fixture-era Stage 1 wording were removed. Runtime inspection uses the saved Job's trusted URL and host allowlist.
4. Assessment input no longer contains `track_id`; the registry's active track is the only stored scope. A two-track direct-dispatch regression proves no cross-track write.
5. External cancellation during a slow tool explicitly cancels and joins child tasks, persists only a truthful cancellation failure when possible, emits one interruption, and records session measurement/settlement.
6. Manual proof now distinguishes text-only CLI `--fake` from the deterministic automated tool trajectory.
7. All three Plan 004 drawio edge styles are orthogonal and PNGs were re-exported from the final XML.
8. Current docs and deliverables report 223 tests, with exact per-file collection recorded in the report below.

## Writer verification

| Check | Result |
|---|---|
| Full pytest suite | 223 passed |
| Focused regression tests | passed |
| `py_compile` | passed |
| `uv lock --check` | passed |
| `git diff --check` | passed |
| XML/cell count/PNG dimension checks | passed |

## Diagram checks

| Diagram | Total `mxCell` | PNG dimensions |
|---|---:|---|
| `employment-models.drawio` | 34 | 640×524 |
| `tool-effects.drawio` | 22 | 744×404 |
| `conversation-trajectory.drawio` | 21 | 464×474 |

All diagram edges include `edgeStyle=orthogonalEdgeStyle`, `orthogonalLoop=1`, and `jettySize=auto`. All PNGs have valid PNG signatures and nonzero dimensions.

## Review boundary

Fresh final review remains controller-owned and pending. The report's live/private proof remains deferred; no approval is claimed here.
