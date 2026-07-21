# Plan 004 Review Ledger

## Review round

Three independent Flash reviews were run against the repair candidate after the initial candidate was rejected. All reviews were architecture/correctness/deliverables scoped. No live provider or private fixture was used.

## Candidates reviewed

| Candidate | Role | Verdict |
|-----------|------|---------|
| `0cbff2b` | Initial Plan 004 implementation | REJECTED (3 findings) |
| `0766d56` | Repair: isolate PTY tests, export PNGs, correct metadata | ACCEPTED with blockers |

## Initial candidate 0cbff2b findings (all repaired at 0766d56)

1. **PTY test isolation.** `tests/test_terminal_pty.py` tests defaulted `HAXJOBS_CAREER_DB` to `state/career_graph.db`, violating the Plan 004 Phase A isolated-synthetic-test rule. Repaired with `_isolated_career_db()` helper creating temp DB from test fixture.

2. **Missing PNG exports.** Three `.drawio` files had no `.png` exports. Exported via `/opt/drawio/drawio -x -f png`.

3. **Report metadata.** Report claimed COMPLETE but listed PTY tests as "failing due to environment" and PNGs as deferred. Corrected to report 216 passes with present PNGs.

## Current correctness repair (626890c)

The approved substitute final reviewer blocked this candidate with reproducible findings. The sole Plan 004 writer repaired the accepted root causes: successful source snapshot mapping, off-loop DNS and blocking transport, no-network trajectory fixtures, job-column DDL and explicit migration, person/track ownership at create and resume, truthful assessment replay results, failed initial-message persistence, and the missing composition cleanup coverage. Focused regressions cover each repair. No live model, public network, private fixture, state database, credential, or manual proof was run.

**Current verdict: final review pending, not approved.**

## Writer verification (0766d56 + Plan 004 repairs)

```
223 passed (full suite after the current correctness repair)
uv lock --check: ok
py_compile all src/ and tests/: ok
git diff --check: ok
```

### Diagram cell counts

| Diagram | Cells (total mxCell) | PNG | Status |
|---------|---------------------|-----|--------|
| employment-models.drawio | 34 (32 non-root) | 640×524 | OK |
| tool-effects.drawio | 22 | 744×404 | OK |
| conversation-trajectory.drawio | 21 | 464×474 | OK |

All PNGs have valid signature and nonzero IHDR dimensions.

## Review round outcomes

### Architecture review: APPROVED

Layer ownership clean. Zero employment imports in agent_core. Stable deterministic IDs. Append-only assessments. Durable tool execution boundaries (persist-before-handler, persist-after-handler). Immutable session configuration. Content-free measurements.

### Correctness and privacy review: APPROVED (nonblocking observation)

- Tool handler signature change to `(input, context)` consistent across all handlers.
- `ToolExecutionContext` is domain-free (no employment fields).
- `persist_message` callback pattern correct; no batch fallback.
- Dangling call detection produces synthetic `unknown_outcome`; no auto-retry.
- Idempotency via `tool_call_id` UNIQUE constraint with typed conflict detection.
- `source_content_hash` computed server-side, never model-supplied.
- Fetched text returned as tool result only, never becomes system instructions.
- DNS rebinding documented as attended local residual risk.

**Close observation (nonblocking):** `tests/test_career_graph.py` exercises the synthetic fixture only; the real private career DB migration is controller-owned. The writer should note this in the report as a known scope boundary.

### Deliverables review: BLOCKED → REPAIRED

Initial deliverable review found three release blockers against candidate `0766d56`:

1. **Missing `review-ledger.md` and `manual-proof.md`.** Both files were absent from `deliverables/004-saved-job-assessment/`. The deliverables README indexed them as "pending" without creating them.
   - **Repair:** Both files created in the Plan 004 repair commit. README updated to index them as present.

2. **Oversized diagram.** `employment-models.drawio` had 36 non-root cells, exceeding the plan limit of under 35.
   - **Repair:** Simplified to 32 non-root cells by removing the separate ConstraintCheck swimlane and noting constraint_checks as an embedded field in the JobAssessment group. PNG re-exported and verified at 640×524.

3. **Stale doc references.** Multiple Plan 004 scoped docs contained stale claims:
   - `docs/HAXJOBS.md` and `README.md` reported "214 tests" and told users to `--ignore=tests/test_terminal_pty.py`.
   - `AGENTS.md` described deleted `agent_core` events/artifacts modules and a deleted "experiment CLI".
   - `docs/GETTING_STARTED.md` pointed normal users to an ignored `state/experiments/fixtures/` path and told users to ignore PTY tests.
   - **Repair:** All stale test counts, module descriptions, CLI references, and ignored path instructions corrected to match the live code at 216 tests with PTY tests included.

## Final approval

Fresh final review is controller-owned and pending. The writer repair commit addresses all three deliverable blockers. No false final approval claims are made here.

No reviewer IDs, credentials, raw private fixture data, or live model outputs are recorded in this ledger.
