# Implementation Plan

## Goal

Deliver the smallest repeatable Stage 0 job-review experiment, then add only the Stage 1 `inspect_job_source(job_ref)` capability, while preserving a Pi-like model-boundary / generic-agent-core / employment-layer / interface split inside `haxjobs`.

## Read Confirmation

The handoff plan template at `/home/hax/haxjobs/.agents/skills/improve/references/plan-template.md` was read. This review applies its requirements for self-contained plans, exact scope, command-based gates, drift checks, explicit deferrals, and STOP conditions.

The requested `/home/hax/haxjobs/context.md` could not be read because it does not exist at that path. This makes the plan conditional on the baseline and decisions not containing additional requirements that were intended to be supplied there.

## Review Findings

1. **BLOCKER — `/home/hax/haxjobs/context.md`**: the required context file is absent (`ENOENT`). Do not claim a fully reconciled plan until the operator confirms it was intentionally removed or restores it for review.
2. **BLOCKER — repository working tree**: the task reports dirty, uncommitted greenfield cleanup, but repository status and diff could not be inspected with the available read-only file tools. A plan cannot have a trustworthy planned-at SHA or drift check while unrelated cleanup is mixed into the worktree. Commit the cleanup as its own reviewed baseline, or move it to a separate worktree; do not use destructive `git clean` or silently stash another person's work.
3. **HIGH — `discussion/006-pi-inspired-haxjobs-architecture.md`**: its frontmatter is `status: discussing`, and the Pi split and physical package split remain marked open. The task wording explicitly requests that split, but the decision record is stale or the request is ahead of it. Before implementation, record only the accepted four-layer split and one-package decision; do not mark unrelated coding-workspace, document-workspace, or shell questions decided.
4. **HIGH — `src/haxjobs/agent/agent.py`**: the existing `Agent` combines provider configuration, the OpenAI-compatible client, provider messages, and both no-tool and tool loops. Extending it would preserve exactly the coupling the decided architecture is meant to remove.
5. **HIGH — `src/haxjobs/agent/registry.py` and `src/haxjobs/agent/agent.py`**: active tools are limited only in schemas sent to the model. `dispatch()` itself does not receive or enforce the active set, so a requested registered tool can execute even if it was not active for that run. The new Stage 1 core must enforce capability membership again at dispatch.
6. **HIGH — `src/haxjobs/agent/__init__.py` and `src/haxjobs/agent/tools.py`**: importing the legacy agent package registers the entire existing tool catalogue through import side effects. The greenfield experiment must not import this registry, otherwise Stage 0 is not genuinely tool-free and Stage 1 does not have a one-tool catalogue.
7. **HIGH — `pyproject.toml`**: Pydantic is not a direct project dependency even though the decided implementation floor requires Pydantic v2 contracts. Do not rely on FastAPI's transitive dependency; add and lock Pydantic explicitly.
8. **MEDIUM — `src/haxjobs/agent/prompt.py`, `src/haxjobs/agent/prompts.py`, and `src/haxjobs/agent/identity.py`**: current prompts implement old onboarding/discovery/scoring behavior and a generic identity, not the short source-labelled Stage 0 job-review contract. Reusing them would leak old product assumptions into the greenfield run.
9. **MEDIUM — `src/haxjobs/cli.py`**: `haxjobs agent ask` is wired to the legacy `Agent`. The experiment should be a new sibling command and thin interface, not another branch inside `cmd_agent_ask`. Migrating or deleting `agent ask` is a later cleanup after the experiment proves the new runtime.
10. **MEDIUM — `discussion/fixtures/003-five-job-sample.md`**: Job 49 has a deliberately truncated source snapshot and Job 328 has only a title-and-URL stub. Machine fixtures must preserve those limitations explicitly; they must not copy the old evaluation prose or unsupported sponsorship/stack claims into model-visible context.
11. **MEDIUM — observability decisions across `discussion/004-minimal-job-native-harness.md` and `discussion/005-implementation-stack-observability-and-verification.md`**: one note asks to preserve exact run inputs/messages while the privacy floor excludes raw prompts, profiles, outputs, and fetched pages from JSONL by default. Resolve this by keeping JSONL metadata redacted while writing exact selected context and transcript only to ignored, local, permission-restricted run artifacts.
12. **LOW — `.gitignore`**: `/state/` and `/reports/` already cover the proposed private career fixture and run artifacts. No new ignore rule is needed. Avoid adding a duplicate experiment-specific rule.
13. **LOW — `diagram/README.md`**: no Stage 0/Stage 1 harness diagram exists. Defer it until runs validate the proposed shape; a diagram before evidence would add documentation churn without helping execute these two slices.

## Plan Sequence

Materialize exactly two executor plans after the baseline blocker is cleared:

- `plans/001-stage-0-observed-job-review.md`
- `plans/002-stage-1-job-source-loop.md`
- `plans/README.md` — two rows only; Plan 002 depends on Plan 001 and its evidence gate.

Each plan must include the cleaned baseline commit SHA and a drift command scoped to its exact files. Do not write either plan against the currently reported dirty tree.

## Tasks

### Plan 001: Stage 0 — one observed, tool-free job review

1. **Establish and attest the baseline before writing code**
   - Files: repository-wide status only; no source modifications.
   - Changes: inspect `git status --short`, `git diff --stat`, and `git diff --cached --stat`; commit the existing greenfield cleanup separately or use a clean worktree. Record `git rev-parse --short HEAD` in `plans/001-stage-0-observed-job-review.md`.
   - Acceptance: the Stage 0 in-scope paths have no pre-existing unstaged or staged changes, and the plan's drift check reports no unexpected changes.
   - STOP: context remains missing without operator confirmation; cleanup ownership is unclear; or cleanup changes any planned Stage 0 path after the plan is written.

2. **Reconcile the accepted architectural decision without broadening scope**
   - File: `discussion/006-pi-inspired-haxjobs-architecture.md`
   - Changes: add a dated decision-ledger update accepting only the conceptual model boundary, agent core, employment layer, and interfaces inside one Python distribution/package. Keep unrelated workspace and shell decisions open unless separately accepted.
   - Acceptance: a grep of the decision ledger shows the four-layer split and one-package choice as decided, while coding tools, document workspaces, and bash remain unchanged/open.

3. **Add the explicit contract dependency**
   - Files: `pyproject.toml`, `uv.lock`
   - Changes: add Pydantic v2 as a direct runtime dependency and regenerate the uv lock. Add no agent framework, HTTP library, telemetry platform, CLI library, or evaluation framework.
   - Acceptance: `uv lock --check` exits 0 and `uv run python -c "import pydantic; assert pydantic.VERSION.startswith('2.')"` exits 0.

4. **Create the model boundary**
   - New files: `src/haxjobs/model/__init__.py`, `src/haxjobs/model/client.py`
   - Changes: define Pydantic contracts for the Stage 0 request, normalized text response, usage when supplied, provider model/stop metadata, and safe provider failure; define a `ModelClient` protocol; implement one OpenAI-compatible adapter using the existing `openai` dependency and the configured provider credential type/location (`~/.haxjobs/haxjobs.toml`) without copying credential values into code, tests, logs, or artifacts. Keep provider-specific request/response handling here.
   - Acceptance: the model package imports without importing `haxjobs.agent`, and a scripted fake can satisfy the protocol without network access.

5. **Create the minimal generic agent core**
   - New files: `src/haxjobs/agent_core/__init__.py`, `src/haxjobs/agent_core/runtime.py`
   - Changes: define internal message and run-result contracts, provider projection, a one-call Stage 0 runner, run/turn IDs, stop reason, and passive event emission. Add a JSONL sink that records safe metadata and ignores observer failures after logging them. Do not add tools, registry, retries, streaming, sessions, compaction, cancellation machinery, save-point machinery, or provider fallback.
   - Acceptance: a fake-model run performs exactly one model call, returns structured final text, emits ordered start/context/model/completion events, and still returns normally when the event sink fails.

6. **Create the employment job-review host and fixtures**
   - New files: `src/haxjobs/employment/__init__.py`, `src/haxjobs/employment/review_job.py`, `discussion/fixtures/004-job-49-review.json`, `discussion/fixtures/005-job-328-review.json`, `discussion/fixtures/006-job-review-rubric.md`
   - Local ignored input: `state/experiments/fixtures/backend-career.json`
   - Changes: validate the career and job fixture shapes with Pydantic; assemble stable Hax rules, the job-review flow, and source-labelled volatile context; hash fixture and prompt versions into a manifest. The checked-in job fixtures should contain only the evidence already preserved in `003-five-job-sample.md`, mark Job 49's description as truncated, and mark Job 328 as a title/URL stub. The local career fixture should contain the smallest truthful backend direction, hard constraints, relevant evidence, provenance labels, and dates; private source references remain local.
   - Acceptance: fixture loading rejects missing source/date/provenance fields; neither checked-in fixture contains old fit scores, old verdict prose, unsupported sponsorship claims, or private career content.

7. **Add the thin CLI interface and local artifact receipt**
   - File: `src/haxjobs/cli.py`
   - Changes: add `haxjobs experiment review-job`; require explicit job fixture, career fixture, and artifacts directory paths; call the employment host only. For each run create `reports/experiments/<run_id>/events.jsonl`, `manifest.json`, `context.json`, `transcript.json`, `result.json`, and `review.md`. JSONL and manifest contain redacted metadata/hashes; exact bounded selected context and transcript remain only in the ignored local directory with restrictive file permissions. Keep `haxjobs agent ask` unchanged temporarily.
   - Acceptance: CLI help lists the experiment command; the fake path creates all six receipts; no artifact or local career fixture appears in `git status --short`.

8. **Add the smallest deterministic Stage 0 test**
   - New files: `tests/fakes.py`, `tests/fixtures/job_review/career.json`, `tests/test_stage0_job_review.py`
   - Changes: use a scripted fake model and synthetic career fixture to prove context order/source labels, one model call, no tools, deterministic manifest hashes, redacted events, complete local receipts, observer failure isolation, and provider error finalization. Test semantic fixture facts rather than snapshotting natural-language prose.
   - Acceptance: `PYTHONPATH=src:. uv run python3 -m pytest -q tests/test_stage0_job_review.py` exits 0 with no network access.

9. **Run and review Job 49, then Job 328**
   - Commands:
     - `PYTHONPATH=src:. uv run haxjobs experiment review-job --job-fixture discussion/fixtures/004-job-49-review.json --career-fixture state/experiments/fixtures/backend-career.json --artifacts-dir reports/experiments`
     - `PYTHONPATH=src:. uv run haxjobs experiment review-job --job-fixture discussion/fixtures/005-job-328-review.json --career-fixture state/experiments/fixtures/backend-career.json --artifacts-dir reports/experiments`
   - Artifacts: complete the generated `review.md` for each run using `discussion/fixtures/006-job-review-rubric.md`.
   - Acceptance: Job 49 is identified as IT support, probably not worth the user's time, with sponsorship unknown and reasons grounded in supplied responsibilities. Job 328 is explicitly insufficient for confident fit, repeats none of the hidden old-evaluation claims, and names source inspection as the next useful check.
   - STOP: do not begin Stage 1 if Job 49 fails the grounding/control rubric, Job 328 does not demonstrate the source-information gap, any material claim is invented, or a complete reviewed live artifact cannot be produced. Make one explainable Stage 0 prompt/context correction and rerun the same fixture instead.

### Plan 002: Stage 1 — one bounded source-inspection tool

10. **Freeze the Stage 1 drift and evidence gate**
    - File: `plans/002-stage-1-job-source-loop.md`
    - Changes: record the Stage 0 completion SHA and exact Job 49/328 run IDs. Quote the Job 328 review finding that source inspection is needed.
    - Acceptance: Stage 0 tests pass at the recorded SHA and both reviewed run directories exist. Plan 002 remains BLOCKED in `plans/README.md` until this holds.

11. **Add core tool contracts and active-set enforcement**
    - New file: `src/haxjobs/agent_core/tools.py`
    - File: `src/haxjobs/agent_core/runtime.py`
    - Changes: add internal assistant tool-call and tool-result messages, a Pydantic-backed tool definition, explicit registry, per-run active names, validation before execution, safe structured failures, original call-order results, and a maximum model-step count. Dispatch must reject unknown, inactive, malformed, and unavailable calls before invoking a handler. Keep execution sequential; one tool does not justify parallel machinery.
    - Acceptance: fake-model trajectories prove final-answer stop, inactive/unknown rejection, malformed argument rejection, tool exception normalization, provider error, and explicit `step_limit` exit without pretending completion.

12. **Implement only `inspect_job_source(job_ref)` in the employment layer**
    - New file: `src/haxjobs/employment/job_source.py`
    - File: `src/haxjobs/employment/review_job.py`
    - Changes: resolve `job_ref` only against the supplied validated fixture; do not accept an arbitrary model-provided URL. Perform bounded HTTP(S) retrieval with public-address and redirect checks, a fixed timeout/byte cap, visible-text extraction, and no credential forwarding. Return a Pydantic result containing `ok`, trusted source reference, source type, final resolved URL when known, observation time, retrieval status, liveness when detectable, bounded content, truncation/warnings, and a safe failure code/message. Retrieved content is untrusted data, never instructions. LinkedIn blocking, a closed role, or unavailable content is a valid result, not a reason to add search/browser fallback.
    - Acceptance: the employment host registers exactly this one tool and activates it only when source inspection is enabled; Stage 0 mode still exposes zero tools.

13. **Extend event and artifact receipts for tool calls**
    - Files: `src/haxjobs/agent_core/runtime.py`, `src/haxjobs/agent_core/tools.py`
    - Changes: emit safe ordered tool-requested/started/completed-or-failed events with IDs, duration, status, and bounded size metadata. Keep arguments, fetched page content, headers, and provider payloads out of JSONL; retain the exact bounded tool result only in the ignored local transcript.
    - Acceptance: observer failure remains passive; one tool failure produces one model-visible structured result and one terminal event without leaking exception internals.

14. **Add the focused Stage 1 test**
    - New file: `tests/test_stage1_job_source_loop.py`
    - Changes: scripted fake paths for one successful source call followed by final text, blocked/unavailable source followed by uncertainty, malformed arguments, unknown/inactive tools, step limit, event order, unsafe URL/redirect rejection, result truncation, and Job 49 no-tool regression. Stub retrieval in every test; unit tests must not use the network.
    - Acceptance: `PYTHONPATH=src:. uv run python3 -m pytest -q tests/test_stage0_job_review.py tests/test_stage1_job_source_loop.py` exits 0.

15. **Rerun Job 328 with the one active tool, then rerun Job 49 as control**
    - Commands:
      - `PYTHONPATH=src:. uv run haxjobs experiment review-job --job-fixture discussion/fixtures/005-job-328-review.json --career-fixture state/experiments/fixtures/backend-career.json --artifacts-dir reports/experiments --inspect-source --max-model-steps 2`
      - `PYTHONPATH=src:. uv run haxjobs experiment review-job --job-fixture discussion/fixtures/004-job-49-review.json --career-fixture state/experiments/fixtures/backend-career.json --artifacts-dir reports/experiments --inspect-source --max-model-steps 2`
    - Acceptance: Job 328 calls only `inspect_job_source`; a failed/blocked fetch preserves uncertainty; a useful fetch changes the answer only through returned evidence. Job 49 should normally answer from supplied evidence without calling the tool. Both runs have completed human rubrics and ordered traces.
    - STOP: do not add web search, browser automation, arbitrary fetch, retries, another provider, another employment tool, or legacy tools to make the live run look successful. Record the failure as Stage 1 evidence.

16. **Run final repository checks and close only these plans**
    - Commands:
      - `PYTHONPATH=src:. uv run python3 -m pytest -q tests/`
      - `PYTHONPATH=src:. uv run python3 -m py_compile $(find src tests cron -name '*.py')`
      - `uv lock --check`
      - `git status --short`
    - Acceptance: commands exit 0; only Plan 001/002 in-scope tracked files are changed; `state/` and `reports/` artifacts remain untracked/ignored; `plans/README.md` has both rows DONE only after their gates pass.

## Files to Modify

- `discussion/006-pi-inspired-haxjobs-architecture.md` — record the specifically accepted four-layer, one-package decision.
- `pyproject.toml` — declare Pydantic v2 directly.
- `uv.lock` — lock the dependency change.
- `src/haxjobs/cli.py` — add the thin experiment interface without moving business logic into argparse handlers.

No existing file under `src/haxjobs/agent/` should be modified in Stage 0 or Stage 1. Importing that package from the new runtime is a STOP condition.

## New Files

### Handoff plans

- `plans/README.md` — two-plan execution index.
- `plans/001-stage-0-observed-job-review.md` — self-contained Stage 0 executor plan.
- `plans/002-stage-1-job-source-loop.md` — self-contained Stage 1 executor plan, gated on reviewed Stage 0 evidence.

### Model boundary

- `src/haxjobs/model/__init__.py` — public model-boundary exports.
- `src/haxjobs/model/client.py` — model contracts, protocol, and one configured OpenAI-compatible adapter.

### Agent core

- `src/haxjobs/agent_core/__init__.py` — public generic-core exports.
- `src/haxjobs/agent_core/runtime.py` — internal messages, bounded loop, events, artifacts, and structured run result.
- `src/haxjobs/agent_core/tools.py` — Stage 1 typed registry, active-set enforcement, validation, and dispatch.

### Employment layer

- `src/haxjobs/employment/__init__.py` — public employment-host exports.
- `src/haxjobs/employment/review_job.py` — job-review fixture/context/prompt assembly and host.
- `src/haxjobs/employment/job_source.py` — the sole Stage 1 source-inspection action.

### Fixtures, rubric, and tests

- `discussion/fixtures/004-job-49-review.json` — machine-readable, source-limited Job 49 fixture.
- `discussion/fixtures/005-job-328-review.json` — machine-readable title/URL-only Job 328 fixture.
- `discussion/fixtures/006-job-review-rubric.md` — human Stage 0/1 review checklist.
- `tests/fakes.py` — scripted model client used by deterministic tests.
- `tests/fixtures/job_review/career.json` — synthetic, non-private career fixture for tests.
- `tests/test_stage0_job_review.py` — Stage 0 contracts, trace, privacy, fixture, and CLI checks.
- `tests/test_stage1_job_source_loop.py` — Stage 1 validation, source, ordering, failure, and limit checks.

### Local ignored inputs and outputs

- `state/experiments/fixtures/backend-career.json` — truthful private career fixture; never commit.
- `reports/experiments/<run_id>/events.jsonl` — redacted lifecycle events.
- `reports/experiments/<run_id>/manifest.json` — versions, IDs, hashes, model settings, and active tools.
- `reports/experiments/<run_id>/context.json` — exact bounded selected model context, local only.
- `reports/experiments/<run_id>/transcript.json` — exact bounded model/tool transcript, local only.
- `reports/experiments/<run_id>/result.json` — structured run result.
- `reports/experiments/<run_id>/review.md` — completed human rubric.

## Dependencies

- Baseline cleanup and missing-context resolution precede both plans.
- Plan 001 tasks 4–8 depend on the direct Pydantic dependency.
- The CLI depends on all three Stage 0 layers but contains no domain logic.
- Stage 1 is blocked until both live Stage 0 fixtures have complete artifacts and human reviews.
- Stage 1 core tool contracts precede the employment source tool and its tests.
- No Stage 2 work begins from this plan; the next change must be selected from observed Stage 1 traces.

## Deferrals

Explicitly defer:

- migration or deletion of legacy `src/haxjobs/agent/` and `haxjobs agent ask`
- company watches, commitments, scheduler, worker, and durable operation storage
- database redesign or import of old development records
- conversations, sessions, compaction, memory retrieval, save points beyond local receipts, steering, and follow-up queues
- skills, extensions, plugins, sub-agents, and workflow engines
- coding/document workspaces and all generic filesystem/shell tools
- approval flows and every external effect
- web UI and API integration
- streaming, provider fallback, generic retry middleware, and a second provider
- OpenTelemetry, Phoenix, hosted traces, model graders, and evaluation platforms
- search/browser fallback for blocked Job 328 retrieval
- architecture diagram until the two experiment stages validate the shape

Add any deferred item only when a saved run demonstrates the concrete failure it solves, except safety/approval/isolation work, which must exist before its corresponding capability is enabled.

## Risks and Residual Risks

- The missing `context.md` may contain scope or baseline facts absent from this review.
- The dirty cleanup may already add/delete paths proposed here; all exact paths remain conditional until status and diff are reviewed.
- The task wording and `discussion/006` disagree on decision maturity. Updating only the accepted ledger entries avoids accidentally deciding shell/workspace questions.
- Two runtimes temporarily coexist: legacy `src/haxjobs/agent/` and the experiment core. This is acceptable only as a bounded experiment; production callers must not migrate piecemeal until the experiment is reviewed.
- OpenAI-compatible providers differ in tool-call and usage details. Keep those differences in `haxjobs.model`; do not flatten them into employment code.
- LinkedIn will likely block ordinary HTTP retrieval. That is expected evidence, not an implementation failure.
- Exact local transcripts contain private career information even though ignored by git. Restrictive permissions and no credential/header capture are mandatory.
- Semantic live-model behavior cannot be guaranteed by pytest; the Markdown review remains a required gate.