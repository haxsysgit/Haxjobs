# Plan 001 deliverables — Stage 0 observed job review

One folder. Every deliverable artifact. No hunting.

## What's here

| File | What |
|---|---|
| `plan.md` | The full implementation plan |
| `report.md` | Implementation report with attestation, call path, verification outputs |
| `job-49.json` | Job 49 fixture — IT Support Analyst at Trainline |
| `job-328.json` | Job 328 fixture — Software Engineer at Oritain (stub) |
| `rubric.md` | Human review rubric for both jobs |
| `003-stage0-observed-job-review.drawio` | Clean Draw.io source diagram |
| `003-stage0-observed-job-review.png` | PNG preview |

## Architecture

Four layers, one model call, no tools:

```
CLI → employment → agent_core → model → redacted local receipts
```

## Outcome

- Job 49: hard constraint failure (IT support ≠ software engineering)
- Job 328: honest "not enough evidence" (title + URL stub only)
- 27 tests pass
- Three independent Flash reviewers: zero findings
