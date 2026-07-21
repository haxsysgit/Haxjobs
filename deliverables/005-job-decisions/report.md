# Plan 005 implementation report

## Status and baseline

Plan 004 is accepted in the live repository: its implementation was finalized at
`8511c0b`, and the current documentation-restamped baseline is `fe9f315`.
The clean pre-change suite passed **248 tests**. Plan 004's plan file still says
`TODO`, but `plans/README.md`, the accepted commit history, and the live code are
the authority; this was reconciled rather than treated as a blocker.

Plan 005 required **zero agent core changes**. All new behavior uses the existing
Plan 004 `ToolExecutionContext`, durable persistence callback, immutable session
scope, and employment registry interfaces.

## Reconciled live-code drift

The written plan described a dict-returning `get_job` action and a full latest
assessment projection. Live Plan 004 callers rely on the no-track action returning
a `Job`, while the tool contract already exposed `latest_recommendation`. The
implementation preserves that existing no-track action contract, adds an explicit
track-scoped projection, and additively extends the tool output with nullable
`latest_assessment` and `latest_decision` fields. No compatibility wrapper or
agent-core adaptation was added.

## What changed

- Added typed `JobDecision` with labels `apply`, `maybe`, `save`, `skip`, and
  `reject`; stable decision IDs derive from the tool call ID.
- Added the append-only `job_decisions` table with monotonic `sequence`, unique
  `decision_id`, and unique `tool_call_id`.
- Added transactional decision insert/replay/conflict handling. Identical call
  IDs replay the original row; different semantic payloads write nothing and
  return a typed `IdempotencyConflict`.
- Added plain actions for recording, latest retrieval, and ordered history.
- Added `record_job_decision` with `INTERNAL_WRITE` and `retry_safe=False`.
  Track scope comes from the employment host and audit provenance comes from
  `ToolExecutionContext.user_message_id`; neither is model input.
- Added explicit natural-language authority instructions and the apply intent
  boundary. No submission, contact, send, queue, pack, or outreach code exists.
- Extended `get_job` tool output with full latest assessment and latest decision
  projections while retaining the Plan 004 compact recommendation field.

## Exact changed paths

### Application code

- `src/haxjobs/employment/errors.py` — shared typed idempotency conflict.
- `src/haxjobs/employment/schema.py` — `JobDecision` model.
- `src/haxjobs/employment/store.py` — decision DDL and transactional/history methods.
- `src/haxjobs/employment/job_actions.py` — decision actions and track projection.
- `src/haxjobs/employment/tools.py` — decision input/output, handler, description,
  and recalled job projections.

### Tests

- `tests/test_job_actions.py` — action-level append/read regression.
- `tests/test_employment_tools.py` — tool validation, scope, conflict, and recall.
- `tests/test_job_decisions.py` — model/store/action/replay/correction/apply/history tests.
- `tests/test_trajectory_job_328.py` — no-decision and ambiguous-reference fake trajectories.

### Deliverables

- `deliverables/005-job-decisions/README.md`
- `deliverables/005-job-decisions/plan.md`
- `deliverables/005-job-decisions/report.md`
- `deliverables/005-job-decisions/review-ledger.md`
- `deliverables/005-job-decisions/manual-proof.md`
- `deliverables/005-job-decisions/rubric.md`
- `deliverables/005-job-decisions/decision-model.drawio`
- `deliverables/005-job-decisions/decision-model.png`
- `deliverables/005-job-decisions/recall-flow.drawio`
- `deliverables/005-job-decisions/recall-flow.png`

## Test and check results

- Pre-change Plan 004 baseline: **248 passed**.
- Focused Plan 005 set after implementation: **44 passed**.
- Full suite after implementation: **269 passed**.
- `PYTHONPATH=src:. uv run -- python3 -m py_compile $(find src tests -name '*.py')`: passed.
- `uv lock --check`: passed.
- `git diff --check`: passed.
- CLI help checks for `haxjobs --help` and `haxjobs chat --help`: passed.
- No test calls a live model, public network, private fixture, or operator database.

## Manual proof

`manual-proof.md` records the isolated SQLite proof metadata and observed
behavior. It intentionally does not claim live provider, private-profile, or
PTY proof. The safe proof covered a skip write, same-call replay, skip-to-save
append correction, empty reason preservation, source user-message linkage, and
`get_job` latest-decision recall.

## Diagrams

- `decision-model.drawio` and `decision-model.png`: JobAssessment remains Hax's
  analysis; JobDecision is a separate append-only user record, keyed by tool call
  ID and linked to the persisted user message ID for audit provenance.
- `recall-flow.drawio` and `recall-flow.png`: a later same-scope session retrieves
  latest assessment and latest decision from employment state through `get_job`.

## Review findings and repairs

The writer's review found and repaired the initial code-shape risks before the
final verification pass: the Plan 004 compact `latest_recommendation` output was
preserved while adding the new nullable projections; idempotency comparison was
made transactional in the decision store; decision scope/audit fields remained
outside the input model; and the diagrams were regenerated after removing
edge-label overlap and literal newline artifacts. No agent-core or state files
were changed.

No independent DeepSeek reviewer sessions or live controller review were run by
this worktree executor; the review ledger says so explicitly rather than claiming
approval that did not occur.

## Deferred controller steps

- Run controller-owned live/provider and human conversation proof with approved
  private fixtures, if desired; do not expose raw career/model text.
- Obtain the three independent review approvals and record their session IDs.
- Record the final commit SHA and artifact hashes in the plan index after review.
- Update the plan/index status only through the controller; this worktree did not
  edit plans.

## Residual risks

1. Natural-language decision parsing is model-mediated; the handler cannot prove
   that a structured call came from a direct user statement.
2. `apply` is intentionally an intent marker only, but future code must preserve
   the absence of submission/outreach side effects.
3. Decision history is append-only and can grow without a retention or archival
   policy.
4. The current single-process SQLite assumption does not provide cross-process
   session locking.

## Final commit

The exact final commit SHA is recorded by the controller after the implementation
commit and any final review. The writer does not self-claim a controller verdict.
