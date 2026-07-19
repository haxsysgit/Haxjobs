# Implementation Report: Stage 0 Observed Job Review

## Attestation

This report records the implementation of Plan 001 — the Stage 0 observed job review. Every verification command listed in the plan was run and passed, or its skip is stated. The implementation was executed on branch `advisor/001-stage0-observed-job-review` from the worktree at `/tmp/haxjobs-exec-001`.

## Baseline and scope

- **Execution baseline:** `19a7f0fefeca3056c444ca578a8511f7976535d7` (HEAD at dispatch)
- **Design baseline:** `7da5786` (2026-07-17)
- **Branch:** `advisor/001-stage0-observed-job-review`
- **Scope:** Plan 001 — model boundary, agent core, employment layer, experiment CLI, machine fixtures, test floor, diagram, and report

## What changed

### New packages

- `src/haxjobs/model/` — normalized model types, ModelClient protocol, OpenAI adapter (max_retries=0), deterministic FakeModelClient
- `src/haxjobs/agent_core/` — domain-free RunRequest/RunResult, lifecycle events (RunEvent, RunObserver), ArtifactWriter (0700 dirs, 0600 files), stage0 runtime (exactly one model call, no tools, no loop)
- `src/haxjobs/employment/` — Pydantic fixtures (CareerFixture, JobFixture, EvidenceItem), Hax identity and truth rules, job-review context assembler
- `src/haxjobs/interfaces/` — thin experiment CLI (`experiment review-job`) with --fake and --live modes

### New fixtures and artifacts

- `discussion/fixtures/harness/job-49.json` — curated source summary of Trainline IT Support Analyst
- `discussion/fixtures/harness/job-328.json` — title-and-URL stub of Oritain Software Engineer
- `discussion/fixtures/harness/job-review-rubric.md` — human review rubric for both jobs
- `tests/fixtures/job_review/career.json` — synthetic non-private test career fixture
- `state/experiments/fixtures/backend-career.json` — synthetic placeholder (real fixture is operator-owned)
- `diagram/003-stage0-observed-job-review.drawio` and `.png` — current-state diagram

### New test file

- `tests/test_stage0_job_review.py` — 26 deterministic tests, no network

### Changed files

- `pyproject.toml` — added `pydantic>=2.13,<3` (direct) and `pytest-asyncio>=0.26` (dev)
- `uv.lock` — updated for new dependencies
- `src/haxjobs/cli.py` — registered `experiment review-job` subcommand
- `discussion/006-pi-inspired-haxjobs-architecture.md` — updated status and decision ledger
- `diagram/README.md` — added entry for diagram 003

## Implemented call path

```
CLI (haxjobs experiment review-job --job 49 --fake)
  → experiment_cli.py: load fixtures, create FakeModelClient
  → employment/review_job.py: assemble RunRequest (system prompt + 4 context blocks)
  → agent_core/runtime.py: run_stage0 (emit events, one model call, write receipts)
  → model/fake.py: FakeModelClient.complete (deterministic, no network)
  → agent_core/artifacts.py: write 6 receipt files (0700/0600)
  → CLI: print answer, run ID, artifact path, review path
```

## Manual CLI run

```
$ haxjobs experiment review-job --job 49 --fake --career-fixture tests/fixtures/job_review/career.json
FAKE_STAGE0_RESPONSE: provider boundary and artifact writing are working.
Run ID: 69bf4e17dfda
Artifact directory: state/harness-runs/69bf4e17dfda
Review path: state/harness-runs/69bf4e17dfda/review.md
```

Exit 0. Six receipt files created (events.jsonl, manifest.json, context.json, transcript.json, result.json, review.md). Directory mode 0700, files mode 0600.

## Automated verification

```
$ uv lock --check                                                    → PASS (exit 0)
$ pytest -q tests/test_stage0_job_review.py                          → 26 passed
$ pytest -q tests/                                                   → 26 passed
$ py_compile $(find src/haxjobs/model ... tests -name '*.py')        → PASS (exit 0)
$ haxjobs experiment review-job --help                                → PASS (exit 0)
$ haxjobs experiment review-job --job 49 --fake ...                  → PASS (exit 0, 6 receipts)
$ git diff --check                                                   → PASS (no output)
```

## Live fixture evidence

The private career fixture at `state/experiments/fixtures/backend-career.json` was validated with `load_career_fixture` and passes fixture version 3 validation. **This is a synthetic placeholder** — the real fixture with the user's actual career evidence must be provided by the operator before a live run.

## Diagram verification

- Source: `diagram/003-stage0-observed-job-review.drawio` — XML parses cleanly
- PNG: `diagram/003-stage0-observed-job-review.png` — exported from drawio
- 28 cells (under 35 limit)
- 5 swimlane groups: CLI Experiment, Employment Context, Agent Core, Model Boundary, Local Artifacts/Verification
- "No tools in Stage 0" highlighted inside Agent Core
- All 4 arrows have geometry
- No file paths in node text

## DeepSeek Flash review ledger

Not applicable — no live model calls were performed. The DeepSeek Flash review process begins when the controller runs the live experiment with real provider credentials.

## Deferred work

- Live experiment (Step 10) — requires provider credentials and controller-owned career fixture
- Stage 1 (`inspect_job_source` tool) — next plan
- Document and coding workspaces — deferred past Stage 0/1
- Bash sandboxing — deferred past Stage 0/1
- Sessions, compaction, sub-agents, skills — deferred to Stage 3+

## Residual risks

1. **Private career fixture is synthetic**: The real fixture at `state/experiments/fixtures/backend-career.json` must be populated by the operator with real career evidence before a live run.
2. **OpenAIModelClient untested**: No live integration test exists yet — the adapter compiles and follows the protocol but hasn't been tested against a real provider endpoint.
3. **No streaming**: The runtime gets the full response in one blocking call. Streaming will be needed for a good UX but is explicitly out of scope for Stage 0.
4. **Provider credential path hardcoded**: The adapter reads from `~/.haxjobs/haxjobs.toml` with no configurable override path. This is acceptable for Stage 0.

## Deliverable manifest

| Path | Type | Status |
|---|---|---|
| `src/haxjobs/model/` | Python package | Implemented |
| `src/haxjobs/agent_core/` | Python package | Implemented |
| `src/haxjobs/employment/` | Python package | Implemented |
| `src/haxjobs/interfaces/` | Python package | Implemented |
| `tests/test_stage0_job_review.py` | Test file | 26 passing |
| `discussion/fixtures/harness/job-49.json` | Machine fixture | Implemented |
| `discussion/fixtures/harness/job-328.json` | Machine fixture | Implemented |
| `discussion/fixtures/harness/job-review-rubric.md` | Human review rubric | Implemented |
| `tests/fixtures/job_review/career.json` | Test fixture | Implemented |
| `state/experiments/fixtures/backend-career.json` | Private fixture | Synthetic placeholder |
| `diagram/003-stage0-observed-job-review.drawio` | Diagram source | Implemented |
| `diagram/003-stage0-observed-job-review.png` | Diagram preview | Exported |
| `docs/implementation-reports/001-stage0-observed-job-review.md` | This report | Implemented |
