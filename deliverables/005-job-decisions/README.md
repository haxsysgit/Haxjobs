# Plan 005 candidate deliverables: User Job Decisions and Conversation Recall

This folder contains the Plan 005 candidate implementation evidence and diagram
artifacts. Final controller review is pending; these files do not claim approval,
live provider proof, or merge.

| Artifact | Purpose |
|---|---|
| `plan.md` | Frozen copy of the Plan 005 plan |
| `report.md` | Candidate repair report and exact verification results |
| `review-ledger.md` | Writer-owned findings and dispositions |
| `manual-proof.md` | Safe isolated proof metadata; no live/private proof claimed |
| `decision-model.drawio` / `.png` | Assessment/decision separation and append-only lifecycle |
| `recall-flow.drawio` / `.png` | Durable decision write and later `get_job` recall |

The current full suite has **274 passed tests**; the focused Plan 005 suite has
**49 passed**. The PNGs were regenerated locally with the installed `drawio`
command. The source XML parses, cell bounds are valid, and the recall connectors
route around boxes and text. No provider, public network, private fixture,
operator state, or live database was used for deterministic proof.
