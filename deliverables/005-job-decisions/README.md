# Plan 005 deliverables: User Job Decisions and Conversation Recall

This folder contains the Plan 005 implementation evidence and diagram artifacts.

| Artifact | Purpose |
|---|---|
| `plan.md` | Frozen copy of the Plan 005 plan |
| `report.md` | Evidence-backed implementation report |
| `review-ledger.md` | Self-review findings and dispositions |
| `manual-proof.md` | Safe isolated proof metadata; no live/private proof claimed |
| `rubric.md` | Acceptance rubric and current status |
| `decision-model.drawio` / `.png` | Assessment/decision separation and append-only lifecycle |
| `recall-flow.drawio` / `.png` | Durable decision write and later `get_job` recall |

The PNGs were exported locally with the installed `drawio` command. Both source
files are XML and contain six grouped swimlanes, thick orthogonal connectors,
and fewer than 35 cells. No provider, public network, private fixture, operator
state, or live database was used for the deterministic proof.
