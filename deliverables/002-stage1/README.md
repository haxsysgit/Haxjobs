# Plan 002: Stage 1 Bounded Source-Inspection Loop

## Contents

- `plan.md` — Implementation plan (copy of `plans/002-stage1-source-inspection-loop.md`)
- `report.md` — Implementation report
- `004-stage1-source-inspection-loop.drawio` — Current-state diagram source
- `004-stage1-source-inspection-loop.png` — Diagram PNG export

## Summary

Stage 1 extends the Stage 0 runtime with a bounded tool-call loop and exactly one
employment tool: `inspect_job_source`. The model receives a `job_ref` string; the
employment layer resolves it to a trusted fixture URL and retrieves bounded current
evidence. The model cannot supply arbitrary URLs.

Key additions:
- `ToolSchema`, `ToolCall` in model boundary
- `ToolRegistry` with explicit active-set enforcement
- Bounded loop in `run_stage0` (max 3 model steps, 1 handler start)
- `JobSourceFetcher` — HTTPS-only, no redirects, public DNS, byte/text caps
- CLI flags `--inspect-source` and `--max-model-steps`
- 35 deterministic tests with socket guard, no network

## Verification

```bash
uv lock --check                    # exit 0
pytest -q tests/                   # 62 passed
py_compile src/... tests/          # exit 0
haxjobs experiment review-job --job 328 --fake --inspect-source  # exit 0, one tool
```

## Stage 0 compatibility

Stage 0 behavior is unchanged. When `active_tools` is empty (no `--inspect-source`),
the runtime makes exactly one model call with zero tool schemas — exactly as before.
