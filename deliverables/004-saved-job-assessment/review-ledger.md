# Plan 004 Review Ledger

## Status

Final review is pending and not approved. This focused writer pass starts at exact `01d2161` and makes one final correctness/artifact repair commit. No live model, public network, private fixture, provider configuration, credential, plan, or state path was used.

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

## Focused repair pass (`de5f14e`)

1. Tool-result persistence failures remain `PERSISTENCE_FAILED`, including cancellation races; the durable dangling-call recovery model is unchanged.
2. Measurement and turn settlement are ordered transactionally from the interface perspective. Failed settlement or measurement emits no `SESSION_SETTLED`, does not skip in-memory counts, and permits a later retry.
3. Employment source-observation and action failures use safe top-level envelopes; secret-string regressions cover both paths. External task cancellation wins over a provider that catches cancellation and emits `RESPONSE_COMPLETED`.
4. `employment-models.drawio` now shows `JobAssessment` essentials (`assessment_id`, `recommendation`, `summary`) while retaining seven groups, `ConstraintCheck`, and 34 non-root cells; the PNG was re-exported.


1. Source DNS validation now requires `ipaddress.ip_address(address).is_global`, including rejection of `100.64.0.1`.
2. Tool cancellation joins and inspects the dispatch task before synthesizing cancellation, so a handler that catches cancellation and commits a success persists/emits the real result.
3. AgentSession history read and host/setup failures return failed results, emit exactly one `TURN_FAILED` plus `SESSION_SETTLED`, and record measurements when storage permits.
4. Chat `--new`/`--resume` modes are mutually exclusive; person/track scope flags require `--new` and are rejected on resume at parser and composition runtime boundaries.
5. Idempotency conflicts use the top-level `{ok:false, code:"idempotency_conflict", error:...}` envelope while same-payload replay remains successful and conflict remains write-free.
6. SessionStore now enforces only nonblank configuration text and preserves arbitrary opaque values; employment composition remains responsible for scope JSON validation.
7. Migration no longer references the deleted private fixture path: CLI migration requires an explicit `--fixture` path.
8. Deterministic regressions cover all seven blockers. The existing trajectory/diagram repairs remain unchanged.

## Diagram attribution

The original PNG exports occurred in earlier repair commit `0766d56`. Diagram cell reductions, orthogonal-edge repairs, and their re-exports occurred in earlier repair commit `0a29152`; the trajectory correction was recorded before this focused pass. The final repair updates `employment-models` with `job_id`, `track_id`, and `tool_call_id` idempotency metadata; all diagrams remain below 35 non-root cells.

## Writer verification

| Check | Result |
|---|---|
| Full pytest suite | 248 passed |
| Focused runtime/employment regression suite (`test_durable_tool_effects.py`, `test_employment_tools.py`, `test_session.py`, `test_turn_runtime.py`) | 88 passed |
| `py_compile` | passed |
| `uv lock --check` | passed |
| `git diff --check` | passed |
| XML/cell count/PNG dimension checks | passed |

## Diagram checks

| Diagram | Total `mxCell` | PNG dimensions |
|---|---:|---|
| `employment-models.drawio` | 36 total / 34 non-root | 784×554 |
| `tool-effects.drawio` | 22 | 744×404 |
| `conversation-trajectory.drawio` | 21 | 464×474 |

All diagram edges include `edgeStyle=orthogonalEdgeStyle`, `orthogonalLoop=1`, and `jettySize=auto`. All PNGs have valid PNG signatures and nonzero dimensions.

## Final correctness/artifact repair (`01d2161`)

1. Partial assistant persistence failures are `PERSISTENCE_FAILED`; no interruption or `SESSION_SETTLED` event is emitted when canonical persistence fails, and exception text remains local to logs.
2. Tool codes use the static agent-core vocabulary; arbitrary handler codes normalize to `tool_failed` before envelopes, canonical messages, events, and provider projection. Secret-code regressions cover envelope and live output.
3. Failed measurement/settlement attempts consume their sequence after durable records exist. Retry and resume paths advance monotonically without duplicate measurement turn numbers.
4. The complete source transport call is bounded by `asyncio.wait_for` and returns typed `fetch_timeout`; documentation notes that a running `to_thread` worker may finish later.
5. Getting-started profile migration commands include the tracked career fixture.
6. Employment-models source and PNG now show all six JobAssessment identity/idempotency fields, seven groups, and 34 non-root cells.

Focused verification: 248 passed; `py_compile`, `uv lock --check`, `git diff --check`, XML cell count, and PNG signature/dimensions passed. Terminal source/tests were not modified. Controller-owned live/manual provider proof remains deferred.

## Review boundary

Fresh final review remains controller-owned and pending. The controller-owned real-provider manual proof remains honestly blank/deferred; no approval is claimed here. The final commit SHA is reported by the writer after commit.
