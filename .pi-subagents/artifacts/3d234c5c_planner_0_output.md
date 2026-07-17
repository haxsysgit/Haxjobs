# Implementation Plan

## Goal

Implement the decided Stage 0 and Stage 1 job-review harness as a new provider-core, agent-core, employment-layer, and CLI interface path inside `haxjobs`, without migrating or disturbing the existing agent runtime.

## Review Findings

- **High — repository working tree:** The user reports a massive dirty tree. Existing changes cannot be distinguished from implementation changes without a scoped baseline. Never reset, clean, stash, or use `git add -A`.
- **High — `discussion/006-pi-inspired-haxjobs-architecture.md`:** The four-layer architecture is still marked “discussing/open.” This plan treats the task’s instruction to match that split as authorization for Stage 0/1 only.
- **High — no `tests/` directory:** Pytest is configured in `pyproject.toml`, but no test tree exists. Stage 0 must create the test floor before live model runs.
- **Medium — `src/haxjobs/agent/agent.py`:** Provider setup, provider calls, message construction, and tool looping are coupled. It has live callers in `cli.py`, `evaluate/run.py`, onboarding, and `product_tools.py`; replacing it during this experiment would unnecessarily expand scope.
- **Medium — `src/haxjobs/agent/registry.py`:** Tool arguments are decoded but not validated against typed Pydantic contracts. Do not reuse this registry for the new Stage 1 trust boundary.
- **Medium — `pyproject.toml`:** Pydantic is currently transitive through FastAPI rather than declared as a direct runtime dependency.
- **Low — `.gitignore`:** `/state/` and `/reports/` already cover private career fixtures and generated experiment artifacts. No ignore change is required.

## Tasks

### 1. **Establish a dirty-tree safety baseline**

- Files: no repository modifications.
- Commands:
  ```bash
  git rev-parse HEAD
  git status --short
  git diff --name-only
  git diff --cached --name-only
  git ls-files --others --exclude-standard
  git status --short -- \
    pyproject.toml uv.lock src/haxjobs/cli.py \
    src/haxjobs/provider src/haxjobs/agent_core src/haxjobs/employment \
    tests diagram/README.md diagram/003-minimal-job-native-harness.drawio \
    diagram/003-minimal-job-native-harness.png \
    discussion/004-minimal-job-native-harness.md
  ```
- Changes:
  - Record the base SHA and scoped status outside the repository or in the execution report.
  - Never clean, reset, stash, or stage unrelated files.
  - Stage eventual changes only with explicit path lists.
- Acceptance:
  - Every in-scope pre-existing modification is identified before editing.
  - Unrelated dirty files remain untouched.

### 2. **Freeze the Stage 0 fixture boundary**

- Files:
  - `src/haxjobs/employment/fixtures/job-49.json`
  - `src/haxjobs/employment/fixtures/job-328.json`
  - `src/haxjobs/employment/fixtures/review-rubric.md`
  - Local only: `state/experiments/backend-career-v1.json`
- Changes:
  - Extract Job 49 and Job 328 into machine-readable fixtures.
  - Include only source-labelled title, employer/source identity as actually known, URL, stored description, source type, and observation date.
  - Exclude old fit scores, old evaluation prose, inferred sponsorship, and cycle reports.
  - Freeze a minimal real backend-career fixture under ignored `state/`; include direction, constraints, and relevant evidence with source type/date. Exclude contact details and unnecessary private identifiers.
  - Add the Job 49 and Job 328 checklist from `discussion/004` as the tracked review rubric.
- Acceptance:
  - Both job fixtures validate through the employment fixture model.
  - Job 328 remains only a title-and-URL stub.
  - The career fixture is owner-reviewed and contains no invented evidence.
  - Confirm package data survives a wheel build:
    ```bash
    uv build
    unzip -l dist/*.whl | grep 'haxjobs/employment/fixtures/job-49.json'
    ```

### 3. **Add the provider-core boundary**

- Files:
  - `pyproject.toml`
  - `uv.lock`
  - `src/haxjobs/provider/__init__.py`
  - `src/haxjobs/provider/contracts.py`
  - `src/haxjobs/provider/openai_compatible.py`
  - `src/haxjobs/provider/fake.py`
  - `tests/provider/test_model_boundary.py`
- Changes:
  - Declare Pydantic v2 directly.
  - Define the minimal normalized contracts: `ModelRequest`, `ModelResponse`, `ToolCall`, `TokenUsage`, and `ModelClient`.
  - Implement one OpenAI-compatible adapter using the existing user provider configuration and environment fallback semantics without logging credentials.
  - Implement a scripted fake provider with ordered responses and explicit provider errors.
  - Keep career and job logic out of this layer.
- Acceptance:
  ```bash
  PYTHONPATH=src:. uv run python3 -m pytest -q tests/provider/test_model_boundary.py
  ```
  Tests prove text normalization, usage normalization, tool-call normalization, scripted ordering, and sanitized provider errors without network access.

### 4. **Implement the Stage 0 agent core and safe artifacts**

- Files:
  - `src/haxjobs/agent_core/__init__.py`
  - `src/haxjobs/agent_core/contracts.py`
  - `src/haxjobs/agent_core/events.py`
  - `src/haxjobs/agent_core/loop.py`
  - `tests/agent_core/test_loop.py`
- Changes:
  - Define internal messages separately from provider request messages.
  - Define `RunResult` with run ID, final text, exit reason, provider/model, turn count, usage, errors, and artifact directory.
  - Implement one frozen request snapshot and one provider call for Stage 0.
  - Emit safe lifecycle events to append-only JSONL. Observer failure must become a warning and must not alter the model result.
  - Create each run directory as `0700` and files as `0600`:
    - `reports/experiments/<run_id>/events.jsonl`
    - `reports/experiments/<run_id>/manifest.json`
    - `reports/experiments/<run_id>/transcript.json`
    - `reports/experiments/<run_id>/result.json`
    - `reports/experiments/<run_id>/review.md`
  - Keep JSONL and manifest redacted. The ignored local transcript may contain normalized exact messages, but never credentials, headers, cookies, or raw provider payloads.
- Acceptance:
  ```bash
  PYTHONPATH=src:. uv run python3 -m pytest -q tests/agent_core/test_loop.py
  ```
  Tests cover event order, one-call enforcement, provider failure, redaction, file permissions, and passive observer failure.

### 5. **Add the employment host and Stage 0 CLI**

- Files:
  - `src/haxjobs/employment/__init__.py`
  - `src/haxjobs/employment/fixtures.py`
  - `src/haxjobs/employment/prompts.py`
  - `src/haxjobs/employment/review_job.py`
  - `src/haxjobs/cli.py`
  - `tests/employment/test_review_job.py`
  - `tests/test_experiment_cli.py`
- Changes:
  - Validate career and job fixtures with Pydantic.
  - Assemble stable Hax instructions, the job-review flow, and four source-labelled context blocks.
  - Hash prompt, fixture, model/settings, active-tool set, and redaction-policy versions into the manifest.
  - Expose one shared `run_job_review(...)` employment action; the CLI must only parse arguments, call it, and render the result.
  - Add:
    ```text
    haxjobs experiment review-job JOB_REF --stage 0
    ```
  - Stage 0 must reject tool calls and configurations allowing more than one model turn.
- Acceptance:
  ```bash
  PYTHONPATH=src:. uv run python3 -m pytest -q \
    tests/employment/test_review_job.py tests/test_experiment_cli.py
  PYTHONPATH=src:. uv run haxjobs experiment review-job --help
  ```
  The fake-provider trajectory produces complete artifacts with an empty active-tool list.

### 6. **Run and review Stage 0 before Stage 1**

- Commands:
  ```bash
  PYTHONPATH=src:. uv run haxjobs experiment review-job job-49 --stage 0
  PYTHONPATH=src:. uv run haxjobs experiment review-job job-328 --stage 0
  ```
- Artifacts:
  - Complete `review.md` in each generated run directory.
  - Job 49 review must attest role-family recognition, grounded mismatch, unknown sponsorship, clear recommendation, and natural tone.
  - Job 328 review must attest insufficient evidence, absence of hidden old-evaluation claims, and source inspection as the next useful action.
- Acceptance:
  - Stage 1 begins only after both human reviews are complete.
  - Job 328 provides recorded evidence that the source tool is needed.

### 7. **Extend the same core for Stage 1**

- Files:
  - `src/haxjobs/agent_core/contracts.py`
  - `src/haxjobs/agent_core/loop.py`
  - `src/haxjobs/agent_core/tools.py`
  - `src/haxjobs/employment/inspect_job_source.py`
  - `src/haxjobs/employment/review_job.py`
  - `src/haxjobs/cli.py`
  - `tests/agent_core/test_loop.py`
  - `tests/employment/test_review_job.py`
  - `tests/test_experiment_cli.py`
- Changes:
  - Add assistant tool-call and linked tool-result internal messages.
  - Define a typed tool registry with Pydantic input validation and separate registered versus active tools.
  - Use one result envelope:
    ```json
    {
      "ok": true,
      "data": {},
      "error": null,
      "metadata": {}
    }
    ```
    Failures use `ok: false`, `data: null`, and typed error code/message.
  - Extend the loop to bounded model → tool → model execution with a default maximum of three model turns.
  - Reject unknown, inactive, malformed, and mismatched-job calls without execution.
  - Implement only `inspect_job_source(job_ref)`.
  - Resolve the URL from the current operation fixture; never accept a model-supplied URL.
  - Enforce public HTTP(S), redirect validation, DNS/IP checks, byte and text limits, HTML-to-text conversion, and explicit `live`, `gone`, `blocked`, or `unavailable` status.
  - Return observation time, source type, final URL when known, bounded content, truncation state, warnings, and failure code.
  - Label fetched content as untrusted source data in the next model request.
  - Add CLI stage:
    ```text
    haxjobs experiment review-job JOB_REF --stage 1 --max-turns 3
    ```
- Acceptance:
  ```bash
  PYTHONPATH=src:. uv run python3 -m pytest -q \
    tests/agent_core/test_loop.py \
    tests/employment/test_review_job.py \
    tests/test_experiment_cli.py
  ```
  Tests cover no-tool completion, one successful tool trajectory, malformed arguments, unknown/inactive tools, current-job enforcement, retrieval failure, step limit, provider error, event order, and no network use.

### 8. **Run Stage 1 and compare against Stage 0**

- Command:
  ```bash
  PYTHONPATH=src:. uv run haxjobs experiment review-job \
    job-328 --stage 1 --max-turns 3
  ```
- Changes:
  - Complete the generated human review.
  - Compare it with the Stage 0 Job 328 review.
  - Record whether source inspection supplied useful evidence or merely produced a valid blocked/unavailable result.
- Acceptance:
  - Hax never claims source inspection succeeded when it failed.
  - No unsupported old evaluation claims appear.
  - The run terminates with a final answer or explicit step-limit result.

### 9. **Document the implemented split with one clean diagram**

- Files:
  - `diagram/003-minimal-job-native-harness.drawio`
  - `diagram/003-minimal-job-native-harness.png`
  - `diagram/README.md`
  - `discussion/004-minimal-job-native-harness.md`
- Changes:
  - Draw four grouped swimlanes: Interface, Employment Layer, Agent Core, Provider Core.
  - Show Stage 0 active tools `[]` and Stage 1 active tools `[inspect_job_source]`.
  - Keep detailed file paths in Markdown, not diagram nodes.
- Acceptance:
  ```bash
  uv run python3 -c \
    "import xml.etree.ElementTree as ET; ET.parse('diagram/003-minimal-job-native-harness.drawio')"
  drawio --export --format png \
    --output /tmp/haxjobs-stage01-diagram.png \
    diagram/003-minimal-job-native-harness.drawio
  test -s /tmp/haxjobs-stage01-diagram.png
  ```
  If `drawio` is unavailable, retain the validated `.drawio`, omit the PNG, and report the deferred export.

### 10. **Run final scoped verification and dirty-tree comparison**

- Commands:
  ```bash
  PYTHONPATH=src:. uv run python3 -m pytest -q tests/
  PYTHONPATH=src:. uv run python3 -m py_compile \
    $(find src tests cron -name '*.py')
  git diff --check -- \
    pyproject.toml uv.lock src/haxjobs/cli.py \
    src/haxjobs/provider src/haxjobs/agent_core src/haxjobs/employment \
    tests diagram discussion/004-minimal-job-native-harness.md
  git status --short
  ```
- Acceptance:
  - All new tests pass.
  - Compilation succeeds.
  - Scoped diff has no whitespace errors.
  - Comparing initial and final status shows no unrelated path was changed by this work.

## Files to Modify

- `pyproject.toml` — declare Pydantic directly.
- `uv.lock` — lock the direct dependency.
- `src/haxjobs/cli.py` — add the thin experiment command.
- `src/haxjobs/agent_core/contracts.py` — extend internal messages for Stage 1.
- `src/haxjobs/agent_core/loop.py` — extend Stage 0’s one-call path into the bounded tool loop.
- `src/haxjobs/employment/review_job.py` — activate no tools in Stage 0 and one tool in Stage 1.
- `diagram/README.md` — index the architecture diagram.
- `discussion/004-minimal-job-native-harness.md` — link the visual.

Do not modify `src/haxjobs/agent/` or migrate its existing callers in Stage 0/1.

## New Files

- `src/haxjobs/provider/__init__.py`
- `src/haxjobs/provider/contracts.py`
- `src/haxjobs/provider/openai_compatible.py`
- `src/haxjobs/provider/fake.py`
- `src/haxjobs/agent_core/__init__.py`
- `src/haxjobs/agent_core/contracts.py`
- `src/haxjobs/agent_core/events.py`
- `src/haxjobs/agent_core/loop.py`
- `src/haxjobs/agent_core/tools.py`
- `src/haxjobs/employment/__init__.py`
- `src/haxjobs/employment/fixtures.py`
- `src/haxjobs/employment/prompts.py`
- `src/haxjobs/employment/review_job.py`
- `src/haxjobs/employment/inspect_job_source.py`
- `src/haxjobs/employment/fixtures/job-49.json`
- `src/haxjobs/employment/fixtures/job-328.json`
- `src/haxjobs/employment/fixtures/review-rubric.md`
- `tests/provider/test_model_boundary.py`
- `tests/agent_core/test_loop.py`
- `tests/employment/test_review_job.py`
- `tests/test_experiment_cli.py`
- `diagram/003-minimal-job-native-harness.drawio`
- `diagram/003-minimal-job-native-harness.png` when export is available.

Local, ignored artifacts:

- `state/experiments/backend-career-v1.json`
- `reports/experiments/<run_id>/events.jsonl`
- `reports/experiments/<run_id>/manifest.json`
- `reports/experiments/<run_id>/transcript.json`
- `reports/experiments/<run_id>/result.json`
- `reports/experiments/<run_id>/review.md`

## Dependencies

1. Dirty-tree preflight precedes all edits.
2. Fixture contracts precede provider and employment tests.
3. Provider core precedes agent core.
4. Agent core precedes the employment host and CLI.
5. Both Stage 0 live reviews must pass before Stage 1 implementation.
6. Stage 1 extends the Stage 0 loop; it must not introduce a second loop.
7. The diagram follows verified code so it describes implemented behavior.

## STOP Conditions

Stop and report without improvising if:

- Any in-scope file already has unowned changes.
- The private career fixture is absent, unsupported, or not owner-reviewed.
- The configured provider is unavailable; do not silently add fallback routing.
- Stage 0 Job 49 invents material claims or cannot identify the IT-support mismatch.
- Stage 0 Job 328 does not establish source inspection as the next useful step.
- Stage 1 appears to require arbitrary browsing, login cookies, CAPTCHA bypass, or credentials.
- The source tool would accept arbitrary model-supplied URLs.
- A test requires live network access.
- A trace contains credentials, authorization data, or unnecessary private career content.
- The change begins migrating existing `src/haxjobs/agent/` callers.
- Focused verification fails twice or requires changes outside the declared scope.

## Deferrals

- Existing agent migration or deletion.
- Company monitoring, scheduling, and durable commitments.
- Database redesign or old-data migration.
- Sessions, follow-up history, compaction, steering, and save-point persistence.
- More employment tools or generic web search.
- Document and employability project workspaces.
- Filesystem tools, shell, and sandboxing.
- Approvals and external effects.
- Streaming, automatic retries, provider fallback, and cancellation.
- Skills, extensions, plugins, sub-agents, and workflow engines.
- Web interface and cloud worker.
- OpenTelemetry, Phoenix, model judges, and PydanticAI.

## Risks

- Live LinkedIn retrieval may be blocked; this is an acceptable structured Stage 1 result.
- Exact local transcripts remain sensitive even when ignored and permission-restricted.
- The new and old provider paths may temporarily coexist and drift; consolidate only during a separately scoped migration.
- The reported dirty tree may cause unrelated full-suite or compilation failures; compare against the preflight baseline before attributing them to this work.
- The architecture note’s open status should be formally updated only after explicit design acceptance.