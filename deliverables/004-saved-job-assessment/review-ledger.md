# Plan 004 Review Ledger

## Status

Final review is pending and not approved. This focused writer pass starts at exact `58f0807` and makes one final correctness/truthfulness repair commit. No live model, public network, private fixture, provider configuration, credential, plan, or state path was used.

## Prior review history

| Candidate | Outcome | Scope |
|---|---|---|
| `0cbff2b` | rejected | Initial Plan 004 implementation; PTY isolation, PNG exports, and report metadata blockers |
| `0766d56` | accepted with blockers | Isolated PTY tests, exported diagrams, and corrected deliverable metadata |
| `626890c` | blocked | Review ledger/manual proof, diagram cell count, and stale documentation blockers identified |
| `65dd9d6` | blocked | Session configuration, tool-event ordering, and assessment/source/cancellation truthfulness defects |
| `0a29152` | accepted with blockers | Lifecycle, scope, cancellation, and diagram edge/cell repairs |
| `58f0807` | accepted with blockers | Partial stream preservation and other correctness repairs; provider-neutral cancelled failure classification remained |

## Final-pass repairs

1. `run_turn()` now treats the provider-neutral `RESPONSE_FAILED` category `cancelled` exactly like cancellation: one `TURN_INTERRUPTED`, an interrupted partial assistant message when text exists, an interrupted `TurnResult`, and no `TURN_FAILED`.
2. Deterministic regressions cover a partial-text cancelled failure directly and through `AgentSession`, including the interrupted measurement and durable partial status.
3. `conversation-trajectory.drawio` now routes resume through the actual `get_job` read path, which reads the current Job and latest assessment for the active track. Resume never routes to or writes `record_job_assessment`.
4. The ledger's SessionStore wording now states that opaque valid JSON values, including strings and lists, are accepted; employment scope validation remains in composition.

## Diagram attribution

The original PNG exports occurred in earlier repair commit `0766d56`. Diagram cell reductions, orthogonal-edge repairs, and their re-exports occurred in earlier repair commit `0a29152`. `58f0807` did not contain diagram export or cell repairs. This final pass changes only the trajectory semantics and re-exports its corrected PNG; all diagrams remain below 35 cells.

## Writer verification

| Check | Result |
|---|---|
| Full pytest suite | 231 passed in 45.83s |
| Focused regression tests | 2 passed |
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
