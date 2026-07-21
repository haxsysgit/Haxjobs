# Plan 004 Review Ledger

## Status

Final review is pending and not approved. This focused writer pass starts at exact `0a29152` and makes one correctness/truthfulness repair commit. No live model, public network, private fixture, provider configuration, credential, plan, or state path was used.

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
8. Current docs and deliverables report 229 tests, with exact per-file collection recorded in the report below.

## Repairs in this focused pass

1. Stream cancellation preserves already-received assistant text as a durable interrupted partial; external task cancellation follows the same truthful boundary.
2. Tool-call and both assistant persistence failure branches emit one `TURN_FAILED`; no completion is claimed.
3. DNS resolution is awaited with a bounded timeout while retaining the `to_thread` cancellation limitation.
4. Source observations preserve string `Job.external_ref` values without integer conversion.
5. Session storage validates only nonblank valid JSON and preserves opaque string/list values; employment scope validation remains in composition.
6. Manual proof now migrates the tracked synthetic fixture into a safe temporary career DB before fake chat, with the fake model's text-only limitation explicit.

## Writer verification

| Check | Result |
|---|---|
| Full pytest suite | 229 passed |
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
