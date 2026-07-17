# Plan 001: Build the Stage 0 observed job review

> **Executor instructions:** You are the sole implementation agent for this plan.
> Use the exact `deepseek-v4-pro` model. Follow every step in order. Run each
> verification command and confirm its expected result before moving on. If a
> STOP condition occurs, stop and report it. Do not improvise, add adjacent
> capabilities, or preserve old code through compatibility wrappers.
>
> **Reviewer instructions:** Implementation is reviewed by three independent
> `deepseek-v4-flash` agents after the executor produces one clean candidate
> commit. Reviewers are read-only. They report findings and never edit code.
> The Pro executor fixes accepted findings. No other model may substitute for
> either role without Arinze's explicit approval.

## Status

- **Priority:** P1
- **Effort:** L
- **Risk:** MED
- **Depends on:** approved clean design baseline and exact-model availability
- **Category:** direction, architecture, tests
- **Planned against design baseline:** commit `5423187`, 2026-07-17, plus the intentional dirty design snapshot described below
- **Working-tree basis:** the intentional dirty greenfield cleanup and the untracked `discussion/` and `diagram/` trees present on 2026-07-17
- **Current status:** BLOCKED until that cleanup and the discussion/diagram sources are committed as one reviewed design baseline, then this plan is restamped against that baseline
- **Index ownership:** the advisor/operator updates `plans/README.md`; the executor must not edit the index

## Baseline gate, run before dispatch

This plan was written while the repository had broad uncommitted cleanup work. An isolated executor worktree created from `5423187` would not contain the discussion notes, fixtures, diagrams, test deletions, or documentation state used to write this plan.

The advisor or operator must first:

1. Review and commit the intentional cleanup plus `discussion/`, `diagram/`, and `docs/harness-primitives/` work. Call this immutable content baseline `DESIGN_BASE_SHA`.
2. Leave the main checkout clean.
3. Update this plan's `Planned against design baseline` field and every `<DESIGN_BASE_SHA>` placeholder to that commit.
4. Commit the restamped plan files separately. The executor starts from that later clean plan commit, but drift is measured from `DESIGN_BASE_SHA` over source and design paths. Do not try to place a commit's own SHA inside itself.
5. Confirm the files listed below match the recorded design.
6. Confirm the orchestration runtime can call the exact models `deepseek-v4-pro` and `deepseek-v4-flash`.

Run:

```bash
test -z "$(git status --porcelain=v1 --untracked-files=all)"
git rev-parse --short HEAD
test -f discussion/004-minimal-job-native-harness.md
test -f discussion/005-implementation-stack-observability-and-verification.md
test -f discussion/006-pi-inspired-haxjobs-architecture.md
test -f discussion/research/2026-07-17-pi-hermes-job-native-harness-study.md
test -f discussion/fixtures/003-five-job-sample.md
test -f diagram/README.md
```

Expected: every command exits 0, the status output is empty, and the current commit is recorded into this plan before execution.

Then run the updated drift check from the design baseline to the clean plan commit:

```bash
git diff --stat <DESIGN_BASE_SHA>..HEAD -- \
  pyproject.toml uv.lock src/haxjobs/cli.py \
  src/haxjobs/model src/haxjobs/agent_core \
  src/haxjobs/employment src/haxjobs/interfaces \
  tests discussion/001-hax-goal-and-run-lifecycle.md \
  discussion/002-durable-work-and-continuity.md \
  discussion/003-company-watch-vertical-slice.md \
  discussion/004-minimal-job-native-harness.md \
  discussion/005-implementation-stack-observability-and-verification.md \
  discussion/006-pi-inspired-haxjobs-architecture.md \
  discussion/research discussion/fixtures diagram docs/implementation-reports
```

Expected: no output. Plan-file changes are intentionally outside this drift path.

**STOP:** do not dispatch an executor while this plan still says `<DESIGN_BASE_SHA>`, while the checkout is dirty, or when either exact DeepSeek model is unavailable. Do not silently fall back to another model.

## Why this matters

HaxJobs currently has an old single-turn agent and an old tool loop, but the greenfield design says to learn from one real job-review run before building sessions, memory, workflows, or a large tool catalogue.

This plan creates the smallest observable Hax:

```text
CLI
-> employment job-review context
-> generic no-tool agent core
-> one provider adapter
-> local private run artifacts
-> human review
```

Job 49 tests whether Hax can reject a technically noisy but wrong career direction. Job 328 tests whether Hax stays honest when the stored vacancy is only a title and URL.

## Decisions this plan implements

The executor has zero access to this conversation, so these decisions are repeated here.

### Decided experiment

From `discussion/004-minimal-job-native-harness.md`:

- freeze one backend-career fixture from the user's real evidence
- review Job 49 first
- review Job 328 second
- Stage 0 has no tools
- use one configured real model and one scripted fake
- save each run and complete a human review
- do not build sessions, compaction, databases, skills, sub-agents, schedulers, company watches, or UI

### Decided stack

From `discussion/005-implementation-stack-observability-and-verification.md`:

- Python owns Hax and employment logic
- Pydantic v2 validates model-facing and trust-boundary data
- use plain Python rather than an agent framework
- use `uv`
- use `argparse`
- use local redacted JSONL, Python logging, pytest, and Markdown human review
- PydanticAI is the first framework to reconsider only after meaningful loop code accumulates

### Architecture direction settled by the current request

For this implementation wave, use Pi's conceptual split inside one Python distribution:

1. `haxjobs.model`: provider and normalized model boundary
2. `haxjobs.agent_core`: domain-free messages, events, run result, and model-call lifecycle
3. `haxjobs.employment`: Hax instructions, career/job fixture contracts, and job-review context
4. `haxjobs.interfaces`: thin CLI-facing adapter

Do not create four distributions or a package monorepo.

This plan does not decide the future document-workspace, coding-workspace, or shell boundaries from `discussion/006`. Those remain later work.

## Current state

### Repository verification baseline

At planning time:

```text
PYTHONPATH=src:. .venv/bin/python -m py_compile $(find src/haxjobs cron -name '*.py')
-> PASS

PYTHONPATH=src:. .venv/bin/python -m pytest -q tests/
-> ERROR: file or directory not found: tests/

uv lock --check
-> PASS
```

The intentional cleanup removed the old test tree. This plan establishes the first greenfield test floor.

### Current dependency declaration

`pyproject.toml` declares FastAPI, Uvicorn, Markdown, OpenAI, and multipart support. Pydantic 2.13.4 is currently installed transitively through FastAPI but is not a direct project dependency.

The new code imports Pydantic directly, so `pyproject.toml` must declare `pydantic>=2.13,<3` and `uv.lock` must record it.

### Current agent coupling to avoid

`src/haxjobs/agent/agent.py` currently owns provider config, OpenAI client creation, provider message dictionaries, one-call execution, and the tool loop in one class.

`src/haxjobs/agent/registry.py` stores a process-global tool catalogue and dispatches by name without receiving the active set for the current run.

Do not extend or import these modules from the greenfield experiment. Two runtimes may coexist temporarily, but there must be no adapter, re-export, or compatibility wrapper between them.

### Fixture facts

`discussion/fixtures/003-five-job-sample.md` is the source for both machine fixtures.

Job 49:

- Trainline IT Support Analyst
- substantial but truncated 5,000-character source snapshot
- Tier 2 internal IT support duties
- wrong broad direction for the user's backend and AI track
- sponsorship is not proven by the stored vacancy evidence

Job 328:

- Oritain Software Engineer, Mid-Level, Full Stack
- stored evidence is only a title and LinkedIn URL stub
- old evaluation details must remain hidden from Hax
- Stage 0 should refuse a confident fit judgement and name source inspection as the next useful step

## Commands you will need

Run from the repository root.

| Purpose | Command | Expected result |
|---|---|---|
| Lock check | `uv lock --check` | exit 0 |
| Focused tests | `PYTHONPATH=src:. uv run python3 -m pytest -q tests/test_stage0_job_review.py` | all tests pass, no network |
| All greenfield tests | `PYTHONPATH=src:. uv run python3 -m pytest -q tests/` | all tests pass |
| Compile | `PYTHONPATH=src:. uv run python3 -m py_compile $(find src/haxjobs/model src/haxjobs/agent_core src/haxjobs/employment src/haxjobs/interfaces tests -name '*.py')` | exit 0 |
| CLI help | `PYTHONPATH=src:. uv run haxjobs experiment review-job --help` | exit 0 and documented options |
| Fake run | `PYTHONPATH=src:. uv run haxjobs experiment review-job --job 49 --fake --career-fixture tests/fixtures/job_review/career.json` | exit 0, prints answer, run ID, artifact path, review path |
| Diff check | `git diff --check` | no output |

Do not run frontend commands. The frontend is intentionally removed in the current greenfield cleanup and is outside this plan.

## Suggested executor toolkit

- Read `.agents/skills/readable-code/SKILL.md` before writing Python.
- Read `.agents/skills/clean-drawio/SKILL.md` before creating the diagram.
- Use standard-library `argparse`, `logging`, `hashlib`, `json`, `pathlib`, `tomllib`, `uuid`, and UTC datetimes where they are enough.
- Use the installed OpenAI-compatible SDK only in the provider adapter.
- Do not add Typer, Click, HTTPX, requests, PydanticAI, LangChain, OpenTelemetry, Phoenix, or another package.

## Scope

### In scope

Existing files that may change:

- `pyproject.toml`
- `uv.lock`
- `src/haxjobs/cli.py`
- `discussion/006-pi-inspired-haxjobs-architecture.md`
- `diagram/README.md`

New tracked files:

- `src/haxjobs/model/__init__.py`
- `src/haxjobs/model/types.py`
- `src/haxjobs/model/client.py`
- `src/haxjobs/model/fake.py`
- `src/haxjobs/agent_core/__init__.py`
- `src/haxjobs/agent_core/types.py`
- `src/haxjobs/agent_core/events.py`
- `src/haxjobs/agent_core/artifacts.py`
- `src/haxjobs/agent_core/runtime.py`
- `src/haxjobs/employment/__init__.py`
- `src/haxjobs/employment/fixtures.py`
- `src/haxjobs/employment/review_job.py`
- `src/haxjobs/interfaces/__init__.py`
- `src/haxjobs/interfaces/experiment_cli.py`
- `discussion/fixtures/harness/job-49.json`
- `discussion/fixtures/harness/job-328.json`
- `discussion/fixtures/harness/job-review-rubric.md`
- `tests/fixtures/job_review/career.json`
- `tests/test_stage0_job_review.py`
- `diagram/003-stage0-observed-job-review.drawio`
- `diagram/003-stage0-observed-job-review.png`
- `docs/implementation-reports/001-stage0-observed-job-review.md`

Local ignored inputs and outputs created during execution:

- `state/experiments/fixtures/backend-career.json`
- `state/harness-runs/<run_id>/events.jsonl`
- `state/harness-runs/<run_id>/manifest.json`
- `state/harness-runs/<run_id>/context.json`
- `state/harness-runs/<run_id>/transcript.json`
- `state/harness-runs/<run_id>/result.json`
- `state/harness-runs/<run_id>/review.md`

### Out of scope

Do not modify:

- `src/haxjobs/agent/`
- `src/haxjobs/product_tools.py`
- `src/haxjobs/db/`
- `src/haxjobs/discovery/`
- `src/haxjobs/evaluate/`
- `src/haxjobs/features/`
- `src/haxjobs/app.py`
- `src/haxjobs/server/`
- `cron/`
- the old SQLite database or schema
- any frontend path
- existing CV variants, packs, reports, intake files, or profile schema
- `discussion/001` through `discussion/005`
- company-watch objects from paused `discussion/003`

Do not delete the legacy agent in this plan. Do not import it either.

## Git and execution workflow

### Branch and worktree

- Execute in an isolated worktree from the clean, restamped baseline.
- Branch: `advisor/001-stage0-observed-job-review`
- Sole writer: `deepseek-v4-pro`
- Commit in logical units. Match the repository's plain sentence commit style, for example: `Build Stage 0 observed job review`.
- Do not push, merge, or open a pull request unless the operator asks.

### Model preflight and dispatch

The Pi advisor/orchestrator owns model selection. The implementation agent cannot prove its own hidden runtime identity.

Before edits:

1. Use Pi's subagent model control to launch a minimal fresh-context, no-write health task with `model: "deepseek-v4-pro"`.
2. Inspect run metadata, not model prose, and confirm the canonical model ID is `deepseek-v4-pro`.
3. Repeat with `model: "deepseek-v4-flash"`.
4. Record only canonical model ID, run/session ID, timestamp, success or safe failure category, and provider request ID when available.
5. Launch the implementation as one isolated-worktree `worker` task with `model: "deepseek-v4-pro"`, `context: "fresh"`, and this full plan as its task.
6. Later launch each review as a separate fresh `reviewer` task with `model: "deepseek-v4-flash"`, the frozen commit range, and one role rubric.
7. Never print or copy provider credentials.

The provider model used by `haxjobs experiment ... --live` is a separate product-runtime setting. It does not need to be v4 Pro or v4 Flash.

**STOP:** if the orchestration layer cannot expose canonical model metadata, either exact model is unavailable, unauthorized, aliased to another model, or rate-disabled. No substitution.

## Steps

### Step 1: Record the accepted implementation boundary

Update only the decision ledger and status text in `discussion/006-pi-inspired-haxjobs-architecture.md`.

Record that this implementation request accepts:

- Pi's conceptual model, agent-core, employment-layer, and interface split
- one Python distribution for now
- Stage 0 and Stage 1 as the first experiment sequence

Keep the document-workspace, coding-workspace, and bash questions open. Do not rewrite the technical study.

**Verify:**

```bash
rg -n "status:|Pi as architecture reference|Physical package split|Coding tools in HaxJobs|Document file tools|Bash" discussion/006-pi-inspired-haxjobs-architecture.md
```

Expected: the four-layer and one-package choices are clearly decided; the three future workspace or shell items remain open.

### Step 2: Declare Pydantic as a direct dependency

Add `pydantic>=2.13,<3` to project dependencies and update `uv.lock` using `uv lock` or `uv add`.

Do not change the Python version or any unrelated dependency.

**Verify:**

```bash
uv lock --check
uv run python3 -c "import pydantic; assert pydantic.VERSION.startswith('2.')"
```

Expected: both commands exit 0.

### Step 3: Create machine-readable, source-limited fixtures

Create `discussion/fixtures/harness/job-49.json` and `job-328.json` from `discussion/fixtures/003-five-job-sample.md`.

Required common fields:

```text
fixture_id
fixture_version
job_ref
observed_at
source_type
source_url
source_status
title
employer_name
location
description
description_kind
content_complete
warnings
```

Rules:

- The current discussion fixture does not contain the literal 5,000-character Job 49 payload. Do not reconstruct or invent it.
- Job 49 contains a clearly labelled curated source summary using only the responsibilities and requirements preserved in `003-five-job-sample.md`.
- Add `description_kind="curated_source_summary"`, `content_complete=false`, and a warning that the original stored snapshot was truncated and the exact raw payload is not present in the design fixture.
- Job 328 contains only the title and source URL stub. Its description must not contain old evaluation details.
- Job 328 uses `source_status="lead_only"` or an equally explicit bounded vocabulary.
- Neither fixture contains old fit scores, fit verdicts, recommended CV variants, old sponsorship risk labels, cycle reports, or model-written evaluation prose.
- Do not infer employer, stack, sponsorship, salary, work mode, or seniority beyond the stored evidence.
- For Job 328, `employer_name` is null or explicitly unknown because the stored row says LinkedIn and the employer identity is not verified by the supplied snapshot. Do not promote the URL slug into verified employer truth.

Create `discussion/fixtures/harness/job-review-rubric.md` with the Job 49, Job 328, engineering, privacy, and voice checks from `discussion/004` and `discussion/005`.

Create `tests/fixtures/job_review/career.json` as a synthetic, non-private test profile. It must resemble the contract but must not copy private contact details or local paths.

**Verify:**

```bash
python3 - <<'PY'
import json
from pathlib import Path
for name in ("job-49.json", "job-328.json"):
    data = json.loads((Path("discussion/fixtures/harness") / name).read_text())
    required = {
        "fixture_id", "fixture_version", "job_ref", "observed_at",
        "source_type", "source_url", "source_status", "title",
        "employer_name", "location", "description", "description_kind",
        "content_complete", "warnings",
    }
    assert required <= data.keys(), (name, required - data.keys())
job328 = json.loads(Path("discussion/fixtures/harness/job-328.json").read_text())
assert len(job328["description"]) <= 250
assert job328["content_complete"] is False
assert job328["description_kind"] == "title_and_url_stub"
job49 = json.loads(Path("discussion/fixtures/harness/job-49.json").read_text())
assert job49["description_kind"] == "curated_source_summary"
assert job49["content_complete"] is False
for forbidden in ("fit_score", "fit_verdict", "sponsorship_risk", "report_markdown"):
    assert forbidden not in job49 and forbidden not in job328
print("fixture contracts: PASS")
PY
```

Expected: `fixture contracts: PASS`.

### Step 4: Create the model boundary

Build `src/haxjobs/model/` without importing any employment or legacy-agent module.

#### Contracts in `model/types.py`

Use Pydantic models for:

- `ModelMessage`: role plus text content for Stage 0
- `ModelRequest`: stable system text, ordered internal messages, model settings
- `ModelUsage`: optional input, output, and total token counts
- `ModelResponse`: final text, provider, exact model, stop reason, optional usage
- `ModelFailure`: safe category and message with no raw provider body

Keep provider-specific raw objects out of these contracts.

#### Protocol and adapter in `model/client.py`

Define an async `ModelClient` protocol with one explicit failure contract:

```python
class ModelClient(Protocol):
    async def complete(
        self, request: ModelRequest
    ) -> ModelResponse | ModelFailure: ...
```

Expected provider, authentication, timeout, rate, and transport failures return `ModelFailure` with a bounded category and safe message. Unexpected programming errors may raise and are caught by the runtime as `internal_model_error`. Do not mix returned failures and provider exceptions without this boundary.

Implement one OpenAI-compatible adapter using `AsyncOpenAI(max_retries=0)`. One Stage 0 model call must mean one provider request attempt rather than one SDK call that may retry underneath. Record a provider request ID when the SDK returns one, but do not fail if the provider omits it.

Read only `~/.haxjobs/haxjobs.toml` with `tomllib`. The accepted schema is `[provider]` with `api_key`, `base_url`, and `model`. Missing keys produce a safe configuration failure. Do not invent environment precedence in this plan. Do not import `haxjobs.features.setup.service` because that would couple the greenfield runtime to the old web setup flow.

The adapter must:

- require configured base URL, model, and credential
- never log credential values or authorization headers
- accept timeout, temperature, and max-token settings
- map the provider response into `ModelResponse`
- turn expected provider failures into a safe typed failure at the boundary
- use no fallback provider or model

#### Scripted fake in `model/fake.py`

The fake receives an ordered list of responses or failures, records requests, and returns the next item. It must never call the network.

**Verify:**

```bash
PYTHONPATH=src:. uv run python3 - <<'PY'
import sys
from haxjobs.model.fake import FakeModelClient
assert "haxjobs.agent" not in sys.modules
print("model boundary: PASS")
PY
```

Expected: `model boundary: PASS`.

### Step 5: Create the domain-free Stage 0 agent core

Build `src/haxjobs/agent_core/`.

#### Internal contracts in `agent_core/types.py`

Define:

- `AgentMessage`
- `RunRequest`
- `RunResult`
- `RunExitReason`

Stage 0 needs only user and assistant text. Keep the internal message type separate from provider `ModelMessage`, even when their first fields look similar.

`RunResult` must carry:

- run ID
- final text or safe failure
- exit reason
- model/provider metadata
- duration
- optional usage
- artifact directory
- observer errors
- artifact errors
- `receipt_complete` boolean

#### Events in `agent_core/events.py`

Define a versioned Pydantic event envelope and an observer protocol.

Stage 0 event order:

```text
run_started
context_prepared
model_started
model_completed OR model_failed
run_completed OR run_failed
```

Events contain safe IDs, timestamps, durations, hashes, counts, provider/model names, and safe error categories. They exclude raw prompts, career data, model text, provider bodies, credentials, headers, and local private paths.

Observer failures are logged and collected in `RunResult.observer_errors`. They do not change the model result.

#### Artifact store in `agent_core/artifacts.py`

Default root: `state/harness-runs`.

Create each run directory with mode `0700`. Write every receipt file with mode `0600` through atomic temp-file replacement. Keep exact selected context and transcript local and ignored by git.

Files per run:

- `events.jsonl`: redacted lifecycle events
- `manifest.json`: versions, hashes, fixture IDs, provider/model settings, app commit when available
- `context.json`: exact bounded selected context, local only
- `transcript.json`: exact bounded messages, local only
- `result.json`: structured run result
- `review.md`: copied human rubric with run metadata

If receipt writing fails, preserve the model outcome in memory, set `receipt_complete=false`, append a safe artifact error when possible, and return a non-zero CLI status. Never claim a complete experiment receipt. The deterministic tests must inject a write failure and assert this result. Every receipt file, including manifest, result, events, and review, uses mode `0600` on POSIX.

#### One-call runtime in `agent_core/runtime.py`

The runtime receives a frozen `RunRequest`, a `ModelClient`, and observers. It:

1. emits start and context events
2. projects internal messages to `ModelRequest`
3. performs exactly one awaited model call
4. maps the response or failure
5. writes local receipts
6. emits completion
7. returns `RunResult`

Do not add a loop, tool registry, retry, streaming, session, compaction, steering, follow-up, cancellation system, save-point system, or database.

**Verify:** focused tests added in Step 8 must prove one model call and exact event order.

### Step 6: Build the employment-layer job review

Build `src/haxjobs/employment/`.

#### Fixture contracts in `employment/fixtures.py`

Define Pydantic contracts for:

- machine job fixture
- frozen career fixture
- source-labelled evidence item
- career direction and hard constraints

Reject fixtures missing source, observation date, or evidence provenance.

The local private fixture at `state/experiments/fixtures/backend-career.json` must contain only the selected backend direction and evidence needed for these two jobs:

- target role direction
- acceptable location/work mode where relevant
- sponsorship requirement as user-stated truth
- a small list of relevant evidence claims with source type and evidence strength
- fixture creation date and version

Exclude name, email, phone, full address, credential values, unrelated career tracks, raw CV text, and private local paths. Use opaque local source references where provenance must remain local.

#### Prompt and context assembly in `employment/review_job.py`

Keep two stable instruction strings:

1. Hax identity and truth rules
2. job-review flow

They must implement the short hypotheses in `discussion/004`, including:

- Hax helps the user get interviews and become more employable
- speak naturally and directly
- do not invent user, job, company, sponsorship, or currentness claims
- distinguish supported facts, user statements, inference, and unknowns
- check hard constraints before softer fit
- explain strongest overlap, blockers, and important unknowns
- if evidence is insufficient, say what should be checked next
- return a natural answer, not a scorecard

Build four labelled volatile blocks in fixed order:

1. user request
2. career direction and constraints
3. relevant evidence
4. job source snapshot

Do not include the old evaluation, whole profile, whole database row, unrelated projects, or company research.

The employment host creates the frozen `RunRequest` and calls the agent core. It contains no provider-specific dictionaries and no artifact-writing implementation.

**Verify:** fixture and context tests in Step 8.

### Step 7: Add the thin experiment CLI

Create `src/haxjobs/interfaces/experiment_cli.py` and register a new sibling command in `src/haxjobs/cli.py`:

```text
haxjobs experiment review-job
```

Arguments:

- `--job {49,328}`
- mutually exclusive required choice: `--fake` or `--live`
- `--career-fixture PATH`
- `--artifacts-dir`, default `state/harness-runs`

Do not expose base URL, credential, model, temperature, timeout, or token flags in Stage 0. Use versioned constants in the employment request and record them in the manifest. Reconsider flags only after a real comparison needs them.

Rules:

- `--fake` returns exactly `FAKE_STAGE0_RESPONSE: provider boundary and artifact writing are working.` and uses no network. It tests plumbing only and must not imitate a Job 49 or Job 328 judgement. If `--career-fixture` is omitted in fake mode, use the tracked synthetic fixture `tests/fixtures/job_review/career.json`.
- `--live` uses the configured provider and performs exactly one model call. Live mode requires `state/experiments/fixtures/backend-career.json` unless the operator supplies another explicit path.
- no implicit live call
- no provider fallback
- print final answer, run ID, artifact directory, and review path
- print safe failure categories to stderr and return non-zero
- if observer/artifact errors occur, preserve the answer but exit non-zero because the experiment receipt is incomplete
- do not modify `haxjobs agent ask`
- keep all employment logic outside argparse handlers

**Verify:**

```bash
PYTHONPATH=src:. uv run haxjobs experiment review-job --help
PYTHONPATH=src:. uv run haxjobs experiment review-job \
  --job 49 --fake \
  --career-fixture tests/fixtures/job_review/career.json
```

Expected: both exit 0; the fake run creates one complete ignored run directory without requiring private setup.

### Step 8: Establish the greenfield deterministic test floor

Create `tests/test_stage0_job_review.py`. Keep helpers local to the test file unless a second test file later proves sharing is useful.

Required tests:

1. Job fixture contracts accept Job 49 and Job 328.
2. Missing source/date/provenance is rejected.
3. Job 49 is marked truncated.
4. Job 328 remains a title/URL stub and contains no old evaluation claims.
5. Context block order is fixed and source-labelled.
6. Scripted fake performs exactly one call.
7. OpenAI-compatible adapter initializes with `max_retries=0`, so Stage 0 has one provider attempt.
8. The core exposes zero tools and sends no tool schema.
9. Event order matches the Stage 0 contract.
10. JSONL excludes raw fixture content, model text, credentials, headers, and private fixture path.
11. Every receipt file remains local, bounded, and mode `0600` on POSIX.
12. Run directory mode is `0700` on POSIX.
13. Deterministic manifest hash is stable for the same fixture and prompt versions.
14. Provider failure returns a safe failed `RunResult` and complete failure events.
15. Observer failure is recorded without changing model output.
16. Injected artifact-write failure preserves the model outcome, sets `receipt_complete=false`, records a safe artifact error, and makes the CLI exit non-zero.
17. CLI fake run exits 0 and creates all six receipt files.
18. Unit tests perform no network calls.
19. No new module imports `haxjobs.agent`.

Do not snapshot complete natural-language output.

**Verify:**

```bash
PYTHONPATH=src:. uv run python3 -m pytest -q tests/test_stage0_job_review.py
```

Expected: all Stage 0 tests pass.

### Step 9: Receive the operator-owned private career fixture

The Pro writer must not read raw CVs, intake files, `state/profile.json`, the old database, or private files from the main checkout.

Before dispatch, the operator creates and approves `state/experiments/fixtures/backend-career.json` from the user's real evidence. Copy or mount only that bounded ignored fixture into the isolated run environment. It may contain:

- one backend career direction
- relevant location and work-mode constraints
- sponsorship requirement as user-stated truth
- a small evidence list with source type, evidence strength, and opaque source references
- fixture creation date and version

It must exclude contact data, credential material, raw document text, immigration-document identifiers, unrelated career tracks, and private local paths.

The operator owns its truthfulness. The writer only validates and consumes it with the same Pydantic contract as the synthetic fixture. Create a SHA-256 hash and record only that hash and fixture version in tracked reports.

**Verify:**

```bash
PYTHONPATH=src:. uv run python3 - <<'PY'
from pathlib import Path
from haxjobs.employment.fixtures import load_career_fixture
p = Path("state/experiments/fixtures/backend-career.json")
fixture = load_career_fixture(p)
assert fixture
print("private career fixture: PASS")
PY
git check-ignore state/experiments/fixtures/backend-career.json
```

Expected: validation passes and `git check-ignore` prints the path.

### Step 10: Run the live Stage 0 experiment in the decided order

This is a controller-owned and human-reviewed phase after the Pro writer's deterministic candidate is committed. The writer must not receive provider credentials and must not fill or approve the human rubric.

The controller runs Job 49 first:

```bash
PYTHONPATH=src:. uv run haxjobs experiment review-job --job 49 --live
```

Pause after the run. Present the final answer and local `review.md` path to Arinze. Resume the same Pro writer only after Arinze completes the rubric and the controller returns a safe verdict, run ID, and artifact hashes. A rejection may authorize one small prompt/context correction or stop the plan. The writer must never mark its own model output as human-approved.

Required broad result:

- identifies internal IT support rather than backend or AI engineering
- uses actual supplied responsibilities
- does not overvalue AI, automation, Azure, or Bash keywords
- keeps sponsorship unknown
- gives a clear probably-not-worth-the-time recommendation
- sounds conversational rather than like an ATS scorecard
- grounds every material claim in supplied context

Then run Job 328:

```bash
PYTHONPATH=src:. uv run haxjobs experiment review-job --job 328 --live
```

Pause again and ask Arinze to complete the second local rubric. Resume the same Pro writer only after an explicit human-review verdict is present and supplied through the controller.

Required broad result:

- notices the evidence is only a title and URL stub
- does not repeat hidden old-evaluation claims
- refuses a confident fit judgement
- names source inspection as the next useful check

One prompt or context correction is allowed only when the failure is explainable, recorded, and followed by rerunning both fixtures. Do not add tools.

**STOP:** if Job 49 still fails the grounding control after one correction, Job 328 does not expose the missing-source problem, the provider is unavailable, or either run lacks a complete receipt and human review. Stage 1 must not start.

### Step 11: Create the current-state diagram

Use `.agents/skills/clean-drawio/SKILL.md`.

Create:

- `diagram/003-stage0-observed-job-review.drawio`
- `diagram/003-stage0-observed-job-review.png`

The diagram shows only the implemented end state, with five groups:

1. CLI experiment
2. employment context
3. no-tool agent core
4. model boundary
5. local artifacts and verification

Show `No tools in Stage 0` clearly inside the agent-core group. Do not show sessions, databases, compaction, sub-agents, source inspection, company watches, or future workers.

Keep file paths out of nodes. Keep the diagram under 35 cells. Use thick group arrows, destination colours, and import-safe XML.

Update `diagram/README.md` with source, PNG, implementation report, and one-sentence current-state description. Add links to the Stage 0 report and diagram under the current-state implementation references in `discussion/006-pi-inspired-haxjobs-architecture.md`.

**Verify:**

```bash
python3 - <<'PY'
from pathlib import Path
import xml.etree.ElementTree as ET
p = Path("diagram/003-stage0-observed-job-review.drawio")
root = ET.parse(p).getroot()
cells = root.findall(".//mxCell")
edges = [cell for cell in cells if cell.get("edge") == "1"]
assert len(cells) <= 35, len(cells)
assert all(edge.find("mxGeometry") is not None for edge in edges)
print({"cells": len(cells), "edges": len(edges)})
PY
drawio --export --format png \
  --output diagram/003-stage0-observed-job-review.png \
  diagram/003-stage0-observed-job-review.drawio
drawio --export --format png \
  --output /tmp/haxjobs-stage0-diagram.png \
  diagram/003-stage0-observed-job-review.drawio
test -s diagram/003-stage0-observed-job-review.png
file diagram/003-stage0-observed-job-review.png | grep -q 'PNG image data'
```

Expected: XML parses, cell count is within the limit, every edge has geometry, the tracked PNG is regenerated after the final XML change, and both exports are valid non-empty PNGs. Reviewer C checks the tracked PNG for clipping, overlaps, connector crossings, and unreadable text. Byte-identical exports are not required because exporter metadata can differ.

### Step 12: Write the implementation evidence report

Create `docs/implementation-reports/001-stage0-observed-job-review.md`.

Use these exact headings:

```text
# Plan 001 implementation report
## Attestation
## Baseline and scope
## What changed
## Implemented call path
## Manual CLI run
## Automated verification
## Live fixture evidence
## Diagram verification
## DeepSeek Flash review ledger
## Deferred work
## Residual risks
## Deliverable manifest
```

Before initial review, the report must contain:

- design baseline SHA
- exact executor model ID from orchestration metadata and statement that no fallback or implementation delegation occurred
- changed-file list
- final call path with exact file and symbol names
- fake and live manual commands
- concise command outputs with exit codes
- Job 49 and Job 328 run IDs, fixture hashes, prompt version, live experiment model, stop reason, and human rubric outcome
- safe bounded answer excerpts only when they contain no private data
- no raw profile, complete prompt, transcript, fetched page, credential, or header
- diagram source and PNG links
- explicit deferrals
- SHA-256 hashes for the draw.io source and PNG

Do not place the report's own hash or its containing commit SHA inside the report. Those values are self-referential. The advisor records the immutable final commit and report hash externally when signing off and in the `plans/README.md` final-commit column.

After the three initial Flash reviews, the same Pro executor always updates `## DeepSeek Flash review ledger`, even when every reviewer returns no finding. Record review session IDs, reviewed candidate SHA, findings, advisor dispositions, repairs, and verification. Commit this report update with any code fixes. The later final Flash verdict is external advisor evidence against that unchanged commit and is not written back into the reviewed report.

The report is the detailed companion document for the diagram.

**Verify:**

```bash
python3 - <<'PY'
from pathlib import Path
p = Path("docs/implementation-reports/001-stage0-observed-job-review.md")
text = p.read_text()
headings = [
    "# Plan 001 implementation report",
    "## Attestation",
    "## Baseline and scope",
    "## What changed",
    "## Implemented call path",
    "## Manual CLI run",
    "## Automated verification",
    "## Live fixture evidence",
    "## Diagram verification",
    "## DeepSeek Flash review ledger",
    "## Deferred work",
    "## Residual risks",
    "## Deliverable manifest",
]
pos = [text.index(h) for h in headings]
assert pos == sorted(pos)
assert "<" + "PLACEHOLDER" + ">" not in text
for target in (
    "../../diagram/003-stage0-observed-job-review.drawio",
    "../../diagram/003-stage0-observed-job-review.png",
):
    assert target in text, target
    assert (p.parent / target).resolve().exists(), target
print("Stage 0 report contract: PASS")
PY
```

Expected: `Stage 0 report contract: PASS`.

### Step 13: Run full plan verification

```bash
uv lock --check
PYTHONPATH=src:. uv run python3 -m pytest -q tests/
PYTHONPATH=src:. uv run python3 -m py_compile \
  $(find src/haxjobs/model src/haxjobs/agent_core \
  src/haxjobs/employment src/haxjobs/interfaces tests -name '*.py')
PYTHONPATH=src:. uv run haxjobs experiment review-job --help
PYTHONPATH=src:. uv run haxjobs experiment review-job \
  --job 49 --fake \
  --career-fixture tests/fixtures/job_review/career.json
git diff --check
git status --short
```

Expected:

- every command exits 0
- fake run produces a complete local receipt
- only in-scope tracked files are changed
- private fixtures and run artifacts do not appear in status

Commit the candidate. Do not push.

## DeepSeek v4 Flash review round

The Pi advisor/orchestrator, not the implementation agent, freezes the candidate commit and dispatches three fresh independent `deepseek-v4-flash` reviewers. Use orchestration metadata to record the canonical model ID, distinct session ID, role, and reviewed commit SHA. Model prose is not proof of model identity. The Stage 0 live experiment may use whichever model is configured in `~/.haxjobs/haxjobs.toml`; that is separate from the Pro/Flash software-delivery team.

Each reviewer receives the same plan, commit range, discussion decisions, and evidence report. They do not receive each other's findings.

### Reviewer A: architecture and scope

Check:

- four-layer separation
- no imports from `haxjobs.agent`
- one provider boundary
- domain-free agent core
- employment rules only in employment layer
- thin CLI
- zero tools
- no speculative framework, session, registry, plugin, workflow, database, or UI work
- every diff hunk maps to a plan step

### Reviewer B: correctness, safety, and tests

Check:

- Pydantic validation at boundaries
- safe provider failures
- exact one-call behavior
- event ordering
- observer failure isolation
- redaction
- local file permissions
- no credential or private-data leakage
- fake tests use no network
- all verification claims match actual command output

### Reviewer C: deliverables and manual use

Check:

- `haxjobs experiment review-job --help`
- fake and live command documentation
- report completeness
- diagram matches implemented current state
- draw.io imports and exports
- PNG is current and readable
- `diagram/README.md` links work
- a human can find and run the experiment without reading source

Each reviewer returns findings only:

```text
ID
Severity: blocker | major | minor | note
Requirement
Evidence
Impact
Required fix
Verification
```

The Pi advisor/orchestrator labels each finding accepted, rejected, or duplicate and sends that ledger to the same Pro executor. The Pro executor fixes every accepted blocker, major, and minor finding, adds regression coverage where useful, reruns the full plan verification, updates the report even when there were no findings, and commits again.

After every repair, run three new independent Flash reviewers with the same three scopes against the repaired commit. If any finds an accepted blocker or major issue, allow one second Pro repair and another full three-reviewer round. If an accepted blocker or major remains after the second repair, stop and replan. Final acceptance requires three approvals on the same unchanged candidate SHA.

The advisor/operator then records the external verdict, immutable final commit SHA, report SHA-256, reviewer session IDs, and date in `plans/README.md`. This does not modify the reviewed source commit.

## Test plan

The authoritative focused test file is `tests/test_stage0_job_review.py`.

Tests are semantic and structural, not prose snapshots. They use the scripted fake. They never call the live provider.

Manual live validation is separate and recorded in local receipts plus the tracked implementation report.

## Done criteria

All must hold:

- [ ] Design baseline was committed, clean, and `<DESIGN_BASE_SHA>` was restamped before dispatch.
- [ ] Orchestration metadata proves exact `deepseek-v4-pro` implemented all code and deliverables.
- [ ] Orchestration metadata proves three independent `deepseek-v4-flash` reviews on every candidate round and three approvals on the same final SHA.
- [ ] Pydantic v2 is a direct dependency and `uv lock --check` passes.
- [ ] New code follows model, agent-core, employment, and interface boundaries.
- [ ] No new module imports `haxjobs.agent`.
- [ ] Stage 0 exposes zero tools and performs exactly one model call.
- [ ] Job 49 and Job 328 fixtures preserve their evidence limits.
- [ ] Synthetic tests contain no private data.
- [ ] Private career fixture and run artifacts remain ignored.
- [ ] Redacted JSONL contains no raw career/job/model text or credentials.
- [ ] Every local receipt file is mode `0600` and each run directory is mode `0700` on POSIX.
- [ ] Exact selected context and transcript exist only in permission-restricted local artifacts.
- [ ] `tests/test_stage0_job_review.py` passes without network.
- [ ] All greenfield tests pass.
- [ ] CLI help and fake run pass.
- [ ] Two live runs exist and Arinze recorded explicit accepted or rejected human-review status for each.
- [ ] Job 49 passes the control rubric.
- [ ] Job 328 demonstrates the missing-source problem.
- [ ] Draw.io XML parses, exports, and matches the current implementation.
- [ ] PNG is non-empty and linked from `diagram/README.md`.
- [ ] Implementation report contains commands, outputs, run evidence, initial reviewer ledger, and diagram/PNG hashes without a self-hash or containing-commit SHA.
- [ ] Advisor/operator recorded external final verdict, immutable commit SHA, report hash, and reviewer session IDs in `plans/README.md`.
- [ ] Every accepted reviewer finding is resolved.
- [ ] `git diff --check` passes.
- [ ] Candidate worktree is clean after the final commit.
- [ ] No out-of-scope file changed.

## STOP conditions

Stop and report without improvising if:

- the baseline gate is not clean or this plan has not been restamped
- orchestration cannot prove exact DeepSeek Pro or Flash model IDs from runtime metadata
- any in-scope file drifted from the restamped plan
- implementing a step requires modifying an out-of-scope file
- the new runtime would need to import or wrap `haxjobs.agent`
- provider credentials would need to be copied into code, tests, logs, reports, or prompts
- the operator-owned bounded career fixture is absent or has not been approved by Arinze
- the private career fixture cannot be made truthful without tracked private data
- a deterministic test needs live network access
- observer or artifact failure cannot be represented without hiding the incomplete receipt
- Arinze has not completed either human rubric
- Job 49 fails grounding after one small prompt/context correction
- Job 328 does not prove the source-information gap
- a verification command fails twice after one reasonable correction
- draw.io cannot import/export the simplified XML
- an accepted blocker or major reviewer finding remains after two repair rounds

## Maintenance notes

- Stage 1 must extend this same core. It must not create another loop.
- The model adapter owns provider-specific formats. Employment code never receives SDK response objects.
- The event schema is private Stage 0 infrastructure, not a promise of the final storage model.
- Local JSONL is an experiment trace, not career memory.
- The legacy agent remains untouched until a later migration plan proves the new runtime should replace it.
- Do not promote a prompt trick into a skill from two fixture runs.
- The next plan is blocked until this report proves Job 328 needs source inspection.
