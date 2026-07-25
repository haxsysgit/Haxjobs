# Plan 005 candidate repair ledger

This is the writer-owned ledger. No independent reviewer sessions were spawned,
and no live/private review was claimed. Final controller review is pending.

| ID | Finding | Decision | Evidence |
|---|---|---|---|
| R-001 | The Plan 004 baseline was documented as 248 tests, while the live baseline was 269. | Restamped current docs and report to the measured 273-test post-repair suite. | `README.md`, `docs/HAXJOBS.md`, `report.md` |
| R-002 | A two-connection SQLite race could leak `sqlite3.IntegrityError` from `record_job_decision`. | Recover the unique constraint winner by `tool_call_id`; classify same payload as replay and differing payload as typed conflict. | `src/haxjobs/employment/store.py`, `tests/test_job_decisions.py` |
| R-003 | The original decision trajectory coverage omitted the requested Job 49 direct skip/correction/apply/resume paths. | Added fake, no-network trajectories with durable history and same-scope recall assertions. | `tests/test_trajectory_job_328.py` |
| R-004 | The model-suggestion test did not first create an assessment. | Scripted a real `record_job_assessment` call before the non-decision reply assertion. | `tests/test_trajectory_job_328.py` |
| R-005 | Model-facing `get_job` recall exposed internal call and audit provenance IDs. | Removed `tool_call_id` and `source_user_message_id` only from recall projections; typed action/store reads retain them. | `src/haxjobs/employment/job_actions.py`, `src/haxjobs/employment/tools.py`, tests |
| R-006 | `recall-flow.drawio` connectors could route through lower boxes/text. | Added explicit around-the-outside orthogonal waypoints and re-exported PNG; XML/bounds checks pass. | `recall-flow.drawio`, `recall-flow.png` |
| R-007 | Current docs and delivery text overstated completion and had stale test counts. | Updated current docs and delivery report/README/ledger to candidate reality, 273 tests, and pending review. Left `plans/README.md` untouched. | `README.md`, `docs/`, `deliverables/005-job-decisions/` |
| R-008 | Independent reviewer approval, controller-owned live/provider proof, and merge status are unavailable to the sole writer. | Deferred honestly; no approval, live proof, or merge claim is made. | `report.md`, `manual-proof.md` |

## Scope checks

- No `src/haxjobs/agent_core/` path changed.
- No `plans/README.md`, `state/`, credentials, private fixtures, provider, public
  network, or operator database was used or changed.
- No application submission, outreach, pack generation, queue, or external effect
  was implemented. `apply` remains an intent-only decision.
