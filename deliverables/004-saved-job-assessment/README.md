# Plan 004 Deliverables: Saved Job Assessment

## Contents

| File | Description |
|------|-------------|
| `plan.md` | Copy of Plan 004 specification |
| `report.md` | Implementation completion report |
| `review-ledger.md` | Reviewer findings and decisions (prior reviews plus focused correctness repair; final review pending) |
| `manual-proof.md` | Controller-owned safe run procedure and CLI verification |
| `employment-models.drawio` | Employment model schema diagram (source) |
| `employment-models.png` | Employment model schema diagram (PNG export, 784×524) |
| `tool-effects.drawio` | Durable tool execution boundary diagram (source) |
| `tool-effects.png` | Durable tool execution boundary diagram (PNG export, 744×404) |
| `conversation-trajectory.drawio` | Full job review trajectory diagram (source) |
| `conversation-trajectory.png` | Full job review trajectory diagram (PNG export, 464×474) |

All PNGs exported via `/opt/drawio/drawio -x -f png`. Each has a valid PNG signature and nonzero IHDR dimensions. `employment-models` has 34 non-root cells, seven model groups, and a separate `ConstraintCheck` group with `constraint_id, constraint_text` and `result (pass | fail | unknown)` fields.

## Key achievements

- 240 automated tests pass (full suite, including PTY terminal tests with isolated temp career DB)
- First state-changing employment workflow: user asks → get_job → inspect → assess
- Durable tool execution boundaries: persist before handler, persist after handler
- Immutable session configuration: person/track scope pinned at creation
- Content-free turn measurements
- Stable deterministic IDs for migration integrity
- Idempotent job assessments with typed conflict detection
- Stage 0/1 experiment runtime deleted after replacement trajectories pass

## Verification

```bash
PYTHONPATH=src:. uv run python3 -m pytest -q tests/            # 238 passed
PYTHONPATH=src:. uv run python3 -m py_compile $(find src tests -name '*.py')  # ok
uv lock --check                                                # ok
git diff --check                                               # ok
```
