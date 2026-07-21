# Plan 004 Review Ledger

## Status

Final review is pending and not approved. This focused writer pass starts at exact `e0390b5` and makes one correctness repair commit. No live model, public network, private fixture, provider configuration, credential, plan, or state path was used.

## Prior review history

| Candidate | Outcome | Scope |
|---|---|---|
| `0cbff2b` | rejected | Initial Plan 004 implementation; PTY isolation, PNG exports, and report metadata blockers |
| `0766d56` | accepted with blockers | Isolated PTY tests, exported diagrams, and corrected deliverable metadata |
| `626890c` | blocked | Review ledger/manual proof, diagram cell count, and stale documentation blockers identified |
| `65dd9d6` | blocked | Session configuration, tool-event ordering, and assessment/source/cancellation truthfulness defects |
| `0a29152` | accepted with blockers | Lifecycle, scope, cancellation, and diagram edge/cell repairs |
| `58f0807` | accepted with blockers | Partial stream preservation and other correctness repairs; provider-neutral cancelled failure classification remained |
| `285f424` | accepted with blockers | Provider cancellation classification repaired; seven further correctness blockers remained |
| `e0390b5` | accepted with blockers | Seven further correctness blockers remained: safe error boundary, settlement ordering, and separate ConstraintCheck artifact |

## Final repair pass (`e0390b5`)

1. Runtime exception/provider/tool validation details are mapped once to stable public error categories. A regression injects secret/path/token/provider-body text and asserts neither `TurnResult` nor `LiveEvent` serialization contains it.
2. Terminal lifecycle ownership moved to `AgentSession`: terminal turn events wait for durable settlement. Settlement failure returns `persistence_failed`, logs the storage exception, emits one generic `TURN_FAILED`, emits no `TURN_COMPLETED` or `SESSION_SETTLED`, and preserves durable messages/measurement for explicit recovery. `TerminalClient` also refuses arbitrary `TURN_FAILED.error` text.
3. `employment-models.drawio` now has seven groups and a separate `ConstraintCheck` group with `constraint_id, constraint_text` and `result`; it has 34 non-root cells and a 784×524 PNG export.


1. Source DNS validation now requires `ipaddress.ip_address(address).is_global`, including rejection of `100.64.0.1`.
2. Tool cancellation joins and inspects the dispatch task before synthesizing cancellation, so a handler that catches cancellation and commits a success persists/emits the real result.
3. AgentSession history read and host/setup failures return failed results, emit exactly one `TURN_FAILED` plus `SESSION_SETTLED`, and record measurements when storage permits.
4. Chat `--new`/`--resume` modes are mutually exclusive; person/track scope flags require `--new` and are rejected on resume at parser and composition runtime boundaries.
5. Idempotency conflicts use the top-level `{ok:false, code:"idempotency_conflict", error:...}` envelope while same-payload replay remains successful and conflict remains write-free.
6. SessionStore now enforces only nonblank configuration text and preserves arbitrary opaque values; employment composition remains responsible for scope JSON validation.
7. Migration no longer references the deleted private fixture path: CLI migration requires an explicit `--fixture` path.
8. Deterministic regressions cover all seven blockers. The existing trajectory/diagram repairs remain unchanged.

## Diagram attribution

The original PNG exports occurred in earlier repair commit `0766d56`. Diagram cell reductions, orthogonal-edge repairs, and their re-exports occurred in earlier repair commit `0a29152`; the trajectory correction was recorded before this focused pass. This pass does not alter diagrams; all diagrams remain below 35 cells.

## Writer verification

| Check | Result |
|---|---|
| Full pytest suite | 240 passed in 45.52s |
| Focused blocker regression suite | 100 passed |
| `py_compile` | passed |
| `uv lock --check` | passed |
| `git diff --check` | passed |
| XML/cell count/PNG dimension checks | passed |

## Diagram checks

| Diagram | Total `mxCell` | PNG dimensions |
|---|---:|---|
| `employment-models.drawio` | 36 total / 34 non-root | 784×524 |
| `tool-effects.drawio` | 22 | 744×404 |
| `conversation-trajectory.drawio` | 21 | 464×474 |

All diagram edges include `edgeStyle=orthogonalEdgeStyle`, `orthogonalLoop=1`, and `jettySize=auto`. All PNGs have valid PNG signatures and nonzero dimensions.

## Review boundary

Fresh final review remains controller-owned and pending. The report's live/private proof remains deferred; no approval is claimed here.
