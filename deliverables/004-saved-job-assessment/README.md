# Plan 004 Deliverables: Saved Job Assessment

## Contents

| File | Description |
|------|-------------|
| `plan.md` | Copy of Plan 004 specification |
| `report.md` | Implementation completion report |
| `review-ledger.md` | Reviewer findings and decisions (pending) |
| `manual-proof.md` | Controller-owned safe run metadata (pending) |
| `employment-models.drawio` | Employment model schema diagram (source) |
| `tool-effects.drawio` | Durable tool execution boundary diagram (source) |
| `conversation-trajectory.drawio` | Full job review trajectory diagram (source) |

PNG exports require local draw.io CLI. Source `.drawio` files are valid XML.

## Key achievements

- 214 automated tests pass (excluding terminal PTY environment tests)
- First state-changing employment workflow: user asks → get_job → inspect → assess
- Durable tool execution boundaries: persist before handler, persist after handler
- Immutable session configuration: person/track scope pinned at creation
- Content-free turn measurements
- Stable deterministic IDs for migration integrity
- Idempotent job assessments with typed conflict detection
- Stage 0/1 experiment runtime deleted after replacement trajectories pass

## Verification

```bash
PYTHONPATH=src:. uv run python3 -m pytest -q tests/ --ignore=tests/test_terminal_pty.py
PYTHONPATH=src:. uv run python3 -m py_compile $(find src tests -name '*.py')
PYTHONPATH=src:. uv run -- haxjobs chat --help
```
