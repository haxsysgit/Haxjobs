# Plan 005 review ledger

This is the writer-owned ledger. No independent reviewer sessions were spawned,
and no live/private review was claimed.

| ID | Finding | Decision | Evidence |
|---|---|---|---|
| R-001 | Plan 004 plan text is stale (`TODO`) while the live accepted baseline is complete. | Reconciled from live `plans/README.md`, commit history, and 248-test baseline; no code blocker. | `fe9f315`, `8511c0b`, pre-change pytest |
| R-002 | Live Plan 004 action callers expect `get_job(store, id)` to return `Job`, while Plan 005 describes a dict projection. | Preserve the no-track `Job` contract and add an explicit track-scoped projection; tool output is additively extended. | `src/haxjobs/employment/job_actions.py`, existing `tests/test_job_actions.py` |
| R-003 | Decision idempotency must not rely on an insert exception or timestamps. | Accepted repair: lookup and insert occur in one store transaction; sequence orders history; semantic conflicts return typed data. | `src/haxjobs/employment/store.py`, `tests/test_job_decisions.py` |
| R-004 | Model must not supply track or audit provenance. | Accepted: input schema has exactly `job_id`, `label`, and `reason`; host/context supply the rest. | `src/haxjobs/employment/tools.py`, tool schema tests |
| R-005 | `apply` could accidentally imply an external application action. | Accepted: only a `JobDecision` row is written; tool description explicitly says intent only; deterministic test checks no external-action surface was added. | `tests/test_job_decisions.py`, `RecordJobDecisionOutput` |
| R-006 | Literal `\\n` diagram text and edge labels reduced readability. | Accepted repair: XML line breaks changed to `&#xa;`, edge labels removed, PNGs regenerated locally. | `decision-model.png`, `recall-flow.png` |
| R-007 | Required independent Flash review and controller-owned live proof are not available to the sole writer. | Deferred honestly; report/manual proof do not claim approval or live/private evidence. | `report.md`, `manual-proof.md` |

## Scope checks

- No `src/haxjobs/agent_core/` path changed.
- No `state/`, credentials, private fixtures, providers, public network, plans,
  migration, fixture loader, CLI, or dependency lock path changed.
- No application submission, outreach, pack generation, queue, or external effect
  was implemented.
