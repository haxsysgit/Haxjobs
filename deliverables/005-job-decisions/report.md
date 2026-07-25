# Plan 005 candidate repair report

## Status

Plan 005 is a candidate implementation on branch `advisor/005-user-job-decisions`.
Final controller review is pending. This report does not claim controller approval,
live provider proof, or merge.

The Plan 004 baseline was 269 passing tests at the start of this repair. The
current full suite is **273 passed**. The focused Plan 005 files are **48 passed**.

Plan 005 required zero `agent_core` changes. The implementation uses the existing
Plan 004 tool execution context, durable message boundary, session configuration,
and employment registry interfaces.

## Repair list

- Repaired `record_job_decision` SQLite idempotency across independent processes.
  A unique-constraint race now reads the committed winner and returns either an
  identical replay or typed `idempotency_conflict`; unrelated integrity errors
  remain visible. A deterministic two-process barrier regression covers both
  same-payload replay and differing-payload conflict.
- Added Job 49 fake conversation trajectories for direct skip, later skip-to-save
  correction, explicit apply, same-scope resume recall, and apply's intent-only
  boundary. The model-suggestion test now records a real assessment before proving
  that a non-decision reply creates no decision.
- Kept `tool_call_id` and `source_user_message_id` durable in store/action models,
  while removing them from model-facing `get_job` assessment and decision recall
  projections.
- Routed `recall-flow.drawio` connectors around, rather than through, the boxes
  and text; regenerated its PNG and validated XML and cell bounds.
- Restamped current README, product/technical/getting-started docs, and the
  delivery README/ledger to describe candidate reality and the 273-test count.
  `plans/README.md` remains controller-owned and was not changed.

## Changed paths

### Application code

- `src/haxjobs/employment/store.py`
- `src/haxjobs/employment/job_actions.py`
- `src/haxjobs/employment/tools.py`

### Tests

- `tests/test_job_decisions.py`
- `tests/test_trajectory_job_328.py`

### Current documentation and delivery evidence

- `README.md`
- `docs/GETTING_STARTED.md`
- `docs/HAXJOBS.md`
- `docs/PRODUCT.md`
- `deliverables/005-job-decisions/README.md`
- `deliverables/005-job-decisions/report.md`
- `deliverables/005-job-decisions/review-ledger.md`
- `deliverables/005-job-decisions/recall-flow.drawio`
- `deliverables/005-job-decisions/recall-flow.png`

No `agent_core`, `plans`, `state`, private fixture, credential, provider, or
public-network path was changed.

## Verification

- `PYTHONPATH=src:. uv run python3 -m pytest -q tests/` — **273 passed**.
- Focused Plan 005 suite (`test_job_actions.py`, `test_employment_tools.py`,
  `test_job_decisions.py`, `test_trajectory_job_328.py`) — **48 passed**.
- `PYTHONPATH=src:. uv run python3 -m py_compile $(find src tests -name '*.py')` — passed.
- `uv lock --check` — passed.
- `git diff --check` — passed.
- CLI help checks for `haxjobs --help` and `haxjobs chat --help` — passed.
- Draw.io XML parse/cell-bound validation and PNG export validation — passed.
- Tests use fake models, isolated SQLite, and harness fixtures only; no provider,
  public network, private fixture, credential, or operator database was used.

## Evidence and residual controller-owned proof

The deterministic tests prove durable skip/save/apply writes, correction history,
current-track recall after resume, omission of internal IDs from recall, and no
submission/outreach/pack/queue surface for `apply`. They do not prove natural
language model reliability beyond the scripted fake trajectories. Controller-owned
work remains: independent review sessions, any approved private/live interaction
proof, human acceptance, and final status/merge decisions.

The final commit SHA is supplied in the completion report after commit; this writer
does not claim a controller verdict.
