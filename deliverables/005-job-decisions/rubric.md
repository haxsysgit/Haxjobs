# Plan 005 acceptance rubric

| Area | Deterministic criterion | Status |
|---|---|---|
| Assessment separation | `JobAssessment` and `JobDecision` are separate models, tables, and tools. | PASS |
| Append-only correction | Skip then save yields two rows; latest uses sequence. | PASS |
| Idempotency | Same call ID replays; different payload conflicts without a second write. | PASS |
| User provenance | `source_user_message_id` comes from `ToolExecutionContext`, not model input. | PASS |
| Track binding | `track_id` comes from the employment host closure, not model input. | PASS |
| Natural-language guard | Tool description requires a direct user statement; ambiguous fake trajectory makes no call. | PASS (v1 semantic guard) |
| Reason truthfulness | Empty user reason remains empty. | PASS |
| Apply safety | `apply` writes only an internal decision row and has no submission/outreach path. | PASS |
| Recall | `get_job` returns nullable latest assessment and decision for the bound track. | PASS |
| Resume scope | Existing Plan 004 immutable session configuration is unchanged. | PASS; no agent-core change |
| No live/private proof | No live provider, public network, private fixture, or operator DB is claimed. | PASS |
| Independent review gate | Three fresh external reviewers approve the same commit. | DEFERRED controller step |
| Human/live acceptance | Controller-owned live trajectory and human rubric. | DEFERRED controller step |
