# Plan 002: Add the Stage 1 bounded source-inspection loop

> **Executor instructions:** You are the sole implementation agent for this plan.
> Use the exact `deepseek-v4-pro` model. Follow every step in order. Run every
> verification command and confirm the expected result. Stop on any stated STOP
> condition. Extend the Stage 0 runtime. Do not create a second loop.
>
> **Reviewer instructions:** Three independent `deepseek-v4-flash` agents review
> the frozen candidate after implementation. They are read-only and report
> findings. The Pro executor fixes accepted findings. No model substitution is
> allowed without Arinze's explicit approval.

## Status

- **Priority:** P1
- **Effort:** L
- **Risk:** HIGH
- **Depends on:** `plans/001-stage0-observed-job-review.md`
- **Category:** direction, architecture, security, tests
- **Planned against:** placeholder commit `5423187`, 2026-07-17
- **Current status:** BLOCKED until Plan 001 lands, its report proves the Job 328 source-information gap, the advisor marks Plan 001 DONE in `plans/README.md`, and this plan is reconciled and restamped to that accepted commit
- **Index ownership:** the advisor/operator updates `plans/README.md`; the executor must not edit the index

## Admission and drift gate

Do not execute this plan from commit `5423187`.

Before dispatch, the advisor must replace `a28d5ba` with the immutable commit accepted after Plan 001's final Flash review. The advisor must also mark Plan 001 DONE and record that commit plus the report hash in `plans/README.md`. Reconcile this plan's expected files and symbols against the live Plan 001 implementation before restamping.

Run:

```bash
test -z "$(git status --porcelain=v1 --untracked-files=all)"
test -f deliverables/001-stage0/report.md
test -f diagram/003-stage0-observed-job-review.drawio
test -f diagram/003-stage0-observed-job-review.png
rg -n "Job 49|Job 328|source inspection|human_review_status" \
  deliverables/001-stage0/report.md
rg -n "001.*DONE.*a28d5ba" plans/README.md
test "$(git rev-parse --short=7 HEAD)" = "$(printf '%s' 'a28d5ba' | cut -c1-7)"
```

Expected:

- clean tree
- Plan 001 report and diagram exist
- report shows Job 49 passed its control rubric
- report shows Job 328 lacked enough source evidence and named source inspection as the next useful check
- `plans/README.md` records Plan 001 as DONE with `a28d5ba` and the external advisor verdict
- current commit equals `a28d5ba`

Then run:

```bash
git diff --stat a28d5ba..HEAD -- \
  src/haxjobs/model src/haxjobs/agent_core \
  src/haxjobs/employment src/haxjobs/interfaces \
  src/haxjobs/cli.py tests discussion/fixtures/harness \
  diagram docs/implementation-reports
```

Expected: no output.

**STOP:** if the Stage 0 evidence does not show that source inspection is needed. Do not build this tool merely because the plan exists.

## Why this matters

Stage 0 should expose a specific failure: Job 328 looks relevant from its title, but its stored evidence is only a title and LinkedIn URL. Hax cannot honestly evaluate it.

Stage 1 adds one thing:

```text
inspect_job_source(job_ref)
```

The model chooses whether it needs that action. Normal Python resolves the trusted fixture URL, retrieves a bounded current observation, and returns structured evidence or an honest failure. Hax then answers from what the tool actually returned.

This plan proves the model-to-tool-to-result loop without adding search, arbitrary URLs, browser automation, another provider, sessions, or a general job workflow.

## Decisions this plan implements

### Decided Stage 1 boundary

From `discussion/004-minimal-job-native-harness.md`:

- Stage 1 adds only `inspect_job_source(job_ref)`
- the model receives a trusted job reference, not arbitrary network-fetch authority
- retrieval code returns evidence and failure, not a fit judgement
- a blocked, unavailable, or closed source is a valid result
- Hax must preserve uncertainty instead of guessing
- maximum tool-step count is required

### Pi-inspired runtime rules

From `discussion/006-pi-inspired-haxjobs-architecture.md` and the converged Pi/Hermes study:

- internal messages remain separate from provider messages
- registered tools and active tools are different sets
- validate arguments before execution
- enforce active capability at dispatch, not only in schemas sent to the model
- preserve the assistant tool-call message before tool results
- append tool results in assistant source order
- turn tool errors into model-visible structured results
- do not execute tool calls from a provider response cut off by output length
- passive event observers cannot control execution
- the loop contains no employment logic

### Privacy and source rules

- fetched pages are untrusted data, never instructions
- JSONL records safe metadata only
- exact bounded tool content stays in ignored local transcripts
- no credentials, headers, raw provider bodies, or full fetched pages enter tracked reports
- unit tests do not call the network

## Expected Plan 001 current state

The executor must confirm these files and symbols exist before editing:

```text
src/haxjobs/model/types.py
  ModelMessage, ModelRequest, ModelResponse, ModelUsage

src/haxjobs/model/client.py
  async ModelClient protocol and configured OpenAI-compatible adapter

src/haxjobs/model/fake.py
  scripted fake and captured requests

src/haxjobs/agent_core/types.py
  AgentMessage, RunRequest, RunResult, RunExitReason

src/haxjobs/agent_core/events.py
  versioned passive lifecycle events

src/haxjobs/agent_core/artifacts.py
  ignored local run receipts

src/haxjobs/agent_core/runtime.py
  one-call, no-tool Stage 0 execution

src/haxjobs/employment/fixtures.py
  source-labelled career and job fixtures

src/haxjobs/employment/review_job.py
  Hax instructions and four-block job-review context

src/haxjobs/interfaces/experiment_cli.py
  haxjobs experiment review-job
```

If Plan 001 used materially different names or boundaries, stop and update this plan before implementation.

## Commands you will need

Run from the repository root.

| Purpose | Command | Expected result |
|---|---|---|
| Stage 0 regression | `PYTHONPATH=src:. uv run python3 -m pytest -q tests/test_stage0_job_review.py` | all pass |
| Stage 1 focused tests | `PYTHONPATH=src:. uv run python3 -m pytest -q tests/test_stage1_source_inspection.py` | all pass, no network |
| Full tests | `PYTHONPATH=src:. uv run python3 -m pytest -q tests/` | all pass |
| Compile | `PYTHONPATH=src:. uv run python3 -m py_compile $(find src/haxjobs/model src/haxjobs/agent_core src/haxjobs/employment src/haxjobs/interfaces tests -name '*.py')` | exit 0 |
| Stage 1 fake run | `PYTHONPATH=src:. uv run haxjobs experiment review-job --job 328 --fake --inspect-source` | exit 0, one tool call, complete receipt |
| Stage 0 mode | `PYTHONPATH=src:. uv run haxjobs experiment review-job --job 328 --fake` | exit 0, zero tools |
| Lock check | `uv lock --check` | exit 0 |
| Diff check | `git diff --check` | no output |

Do not install a new HTTP, HTML, agent, telemetry, or evaluation dependency. Use the Python standard library for this bounded retrieval experiment.

## Suggested executor toolkit

- Read `.agents/skills/readable-code/SKILL.md` before editing Python.
- Read `.agents/skills/systematic-debugging/SKILL.md` if the live source behaves differently from tests.
- Read `.agents/skills/clean-drawio/SKILL.md` before creating the diagram.
- Use `urllib.request`, `urllib.parse`, `html.parser`, `socket`, `ipaddress`, `hashlib`, and UTC datetimes where they hold.
- Treat source content as hostile input.

## Scope

### In scope

Existing files that may change:

- `src/haxjobs/model/types.py`
- `src/haxjobs/model/client.py`
- `src/haxjobs/model/fake.py`
- `src/haxjobs/agent_core/types.py`
- `src/haxjobs/agent_core/events.py`
- `src/haxjobs/agent_core/artifacts.py`
- `src/haxjobs/agent_core/runtime.py`
- `src/haxjobs/agent_core/__init__.py`
- `src/haxjobs/employment/fixtures.py`
- `src/haxjobs/employment/review_job.py`
- `src/haxjobs/employment/__init__.py`
- `src/haxjobs/interfaces/experiment_cli.py`
- `src/haxjobs/cli.py`
- `discussion/fixtures/harness/job-49.json`
- `discussion/fixtures/harness/job-328.json`
- `discussion/fixtures/harness/job-review-rubric.md`
- `discussion/006-pi-inspired-haxjobs-architecture.md` (links to the implemented Stage 1 report and diagram only)
- `tests/test_stage0_job_review.py`
- `diagram/README.md`

New tracked files:

- `src/haxjobs/agent_core/tools.py`
- `src/haxjobs/employment/job_source.py`
- `tests/test_stage1_source_inspection.py`
- `diagram/004-stage1-source-inspection-loop.drawio`
- `diagram/004-stage1-source-inspection-loop.png`
- `docs/implementation-reports/002-stage1-source-inspection-loop.md`

### Deliverable folder

After implementation, collect every deliverable artifact into
**one labelled folder**:

```text
deliverables/002-stage1/
├── plan.md
├── report.md
├── 004-stage1-source-inspection-loop.drawio
├── 004-stage1-source-inspection-loop.png
└── README.md
```

Copy sources in — do not symlink. Code and test fixtures stay in `src/`
and `tests/`. This folder is for the reviewer.

Local ignored outputs:

- `state/harness-runs/<stage1-run-id>/`

### Out of scope

Do not modify: (resolved by greenfield wipe at a28d5ba)

- provider credential setup UI or config writer
- application, outreach, messaging, approval, or submission code
- frontend code
- company-watch records or schedulers
- document or project workspace tools
- any generic `read`, `grep`, `find`, `ls`, `write`, `edit`, or `bash` tool
- discussion notes other than the fixture rubric and the two Stage 1 links allowed in `discussion/006`
- Plan 001 implementation report except to link it from the new report

Do not add search, arbitrary URL fetch, Playwright, browser automation, source fallback, retry middleware, parallel dispatch, sessions, compaction, skills, sub-agents, plugins, or workflows.

## Git and execution workflow

- Worktree: isolated from the clean Plan 001 final commit
- Branch: `advisor/002-stage1-source-inspection-loop`
- Sole writer: exact `deepseek-v4-pro`
- Reviewers: three independent exact `deepseek-v4-flash` contexts on every candidate round; final acceptance requires three approvals on one SHA
- Commit style: plain sentence, for example `Add bounded job source inspection loop`
- Do not push, merge, or open a pull request unless instructed

The Pi advisor/orchestrator runs exact-model health tasks and inspects orchestration metadata before edits. Launch the sole writer with explicit `model: "deepseek-v4-pro"`, fresh context, and isolated worktree. Launch each reviewer separately with explicit `model: "deepseek-v4-flash"`, fresh context, and the frozen commit. Record only canonical model IDs, session IDs, times, result categories, reviewed commit, and provider request references. Stop when metadata is unavailable, the model is mismatched, or either model cannot run. Product live-run model configuration remains separate.

## Steps

### Step 1: Freeze Stage 0 evidence and define the Stage 1 delta

Read the final tracked Plan 001 report. The ignored local Job 328 rubric does not move into a fresh worktree and must not be copied there. The tracked report is the complete admission gate and must contain the safe human verdict and evidence hash.

Record in the new implementation report draft:

- Plan 001 final SHA
- Job 49 and Job 328 Stage 0 run IDs
- the exact safe summary of why Job 328 needed current source inspection
- no raw career context or transcript

Run the Stage 0 tests before changing code.

**Verify:**

```bash
PYTHONPATH=src:. uv run python3 -m pytest -q tests/test_stage0_job_review.py
```

Expected: all tests pass.

### Step 2: Extend the model boundary with normalized tool calls

Update `src/haxjobs/model/types.py` with provider-neutral Pydantic contracts:

- `ToolSchema`
- `ToolCall`
- assistant response content plus ordered tool calls
- tool-result message content for provider projection

Update `ModelRequest` to carry an ordered active-tool schema list. Default is empty.

Update `ModelResponse` to carry ordered tool calls. Default is empty.

Update the OpenAI-compatible adapter in `model/client.py`:

- map active tool schemas into the provider request only when non-empty
- map provider tool calls into internal `ToolCall` values
- preserve call ID, name, and raw argument text
- preserve provider stop reason
- never pass SDK objects beyond the model boundary
- never silently repair malformed argument JSON in the adapter

Update the scripted fake to return sequences such as:

```text
ToolCall(inspect_job_source, {"job_ref":"328"})
FinalText(...)
```

If a provider response ends because of output length and includes tool calls, mark them unsafe for execution. The agent core will return structured failures for those calls.

**Verify:** focused tests in Step 7 must prove empty tools for Stage 0 and normalized ordered calls for Stage 1.

### Step 3: Add the explicit tool registry and active-set enforcement

Create `src/haxjobs/agent_core/tools.py`.

Define a small `ToolDefinition` containing:

- name
- description
- Pydantic input model
- required Pydantic output model
- async handler
- maximum safe model-visible result size

Define one explicit registry. Do not use import-time global discovery, AST scanning, plugin shadowing, availability TTL caches, or dynamic schema mutation.

The registry must support:

- duplicate-name rejection
- schema generation from the Pydantic input model
- ordered active definitions
- dispatch that receives the active set
- unknown-tool failure
- inactive-tool failure
- malformed JSON failure
- Pydantic validation failure
- safe handler exception failure
- model-visible success and failure envelopes

Use one predictable result shape:

```json
{"ok": true, "data": {}}
```

or:

```json
{"ok": false, "code": "...", "error": "..."}
```

A handler exception must not expose traceback, credentials, headers, private paths, or response bodies to the model.

Dispatch is sequential in Stage 1. Parallel execution is deferred.

**Verify:** unit tests must call dispatch with a registered but inactive tool and prove the handler was never invoked.

### Step 4: Turn the one-call runtime into one bounded loop

Extend `src/haxjobs/agent_core/runtime.py`. Do not add a second runtime function that duplicates Stage 0.

Required loop:

```text
prepare frozen request
-> call model
-> if response has tool calls, preserve the complete assistant message
-> validate and dispatch calls in source order
-> append ordered tool results
-> call model again
-> if response has text and no tool calls, stop
-> otherwise stop on explicit error or limit
```

Rules:

- default active tools remain empty
- Stage 0 path behaves exactly as before
- Stage 1 receives one active tool name
- maximum model steps default to 3 and hard cap at 5
- maximum handler starts for this review is 1
- malformed, unknown, inactive, Pydantic-invalid, and truncated calls do not consume the handler budget because no handler starts
- the first valid active call consumes the execution budget when its handler starts
- after one handler starts, every later valid active call returns `tool_budget_exhausted`
- every requested call still receives exactly one result in source order
- when a provider response contains both text and tool calls, tool calls take precedence; preserve the text in the assistant message but do not treat it as the final answer
- a response with neither text nor tool calls returns explicit `empty_model_response`
- unknown, inactive, malformed, invalid, or truncated calls become tool-result failures
- every requested call gets a corresponding result message
- provider error stops with an explicit failed result
- step-limit exit is `limit_reached`, not success text
- preserve assistant tool-call message before results
- preserve tool-result ordering, including mixed invalid and valid calls
- do not add automatic retries
- observer failures remain passive and collected

Add event kinds:

```text
tool_requested
tool_started
tool_completed
tool_failed
```

Events include safe call IDs, name, timing, status, and bounded size metadata. They exclude arguments and result text.

Update local transcript receipts to contain exact bounded call arguments and results. Keep them ignored and mode `0600`.

**Verify:** tests prove Stage 0 still makes one call with no schemas and Stage 1 follows the expected message order.

### Step 5: Implement `inspect_job_source(job_ref)`

Create `src/haxjobs/employment/job_source.py`.

#### Input

```text
job_ref: string
```

The model cannot supply a URL.

The employment host resolves `job_ref` only against the currently loaded, validated job fixture. Reject any other reference.

#### Trusted source configuration

The existing fixture `source_url` is the canonical source URL. Do not add a duplicate `canonical_source_url` field.

Add only `allowed_source_hosts`, an exact fixture-owned host list. Do not accept wildcard domains or derive trust from model text. The tool rejects a fixture when its URL host is absent from this list.

#### Retrieval boundary

This is a trusted-fixture experiment, not a general URL-fetch service. Use a standard-library policy wrapper around an injected resolver and transport so tests exercise the real validation and byte/text limiting while replacing only DNS and socket I/O.

Requirements:

- HTTPS only
- reject URL userinfo, fragments, non-default ports, and IP-literal hosts
- exact normalized host membership in `allowed_source_hosts`
- resolve all A and AAAA candidates and reject the request if any candidate is loopback, private, link-local, multicast, reserved, or unspecified
- disable ambient environment proxies with an explicit empty proxy handler
- disable automatic redirects entirely in Stage 1
- return a structured `redirected` observation containing only the safe target host and status, without fetching the target
- no local file URLs
- no cookies, browser profile, credential, or authorization forwarding
- fixed user agent and `Accept-Encoding: identity`
- allow only bounded textual content types such as HTML or plain text
- 15-second total timeout
- read at most 512 KB plus one byte so overflow is detectable
- 12,000-character model-visible text cap
- record byte and text truncation
- decode declared charset when safe, then UTF-8 replacement fallback
- extract readable visible text with `html.parser`
- no JavaScript execution

Because hostname connection may resolve again below `urllib`, record this as a residual limit of the trusted-fixture experiment. Do not generalize this fetcher to user/model URLs or unattended broad web access. If a later capability needs that, STOP and design a connection-pinned or isolated network service instead of weakening this boundary.

#### Output

Return a typed observation containing:

- `ok`
- job reference
- requested source reference
- final URL when known
- source type
- observed UTC time
- retrieval status: `current`, `redirected`, `blocked`, `gone`, `rate_limited`, `unavailable`, or `invalid_source`
- liveness only when detectable
- bounded visible text
- content hash
- truncation flag
- warnings
- safe failure code and message when needed

Map status deterministically:

- `current`: acceptable 2xx textual response with useful public content
- `redirected`: 3xx response; return the safe target host and do not follow it
- `blocked`: 401 or 403
- `rate_limited`: 429
- `gone`: 404 or 410
- `unavailable`: DNS, timeout, connection, decode, empty-content, or unsupported-response failure
- `invalid_source`: fixture, scheme, hostname, address, port, userinfo, fragment, or host-policy rejection

Do not infer a login wall from vague page text. If a deterministic content rule is later needed, add a fixture and test first.

Do not return a fit score or recommendation.

Treat LinkedIn blocking as expected evidence. Do not add search or browser fallback.

### Step 6: Register exactly one employment tool

Update `src/haxjobs/employment/review_job.py` to create a registry containing only `inspect_job_source` for Stage 1.

Stage 0 passes an empty active set.

Stage 1 passes exactly `{"inspect_job_source"}`.

The active tool description must tell the model:

- use it when the supplied job evidence is insufficient or may be stale
- the argument is the supplied `job_ref`
- it returns source evidence, not fit judgement
- blocked or unavailable is a valid result
- never infer missing facts after a failure

Fetched text enters the model as untrusted evidence with source and observation labels. It must not be inserted into the system prompt.

Define this exact factory signature so callers do not invent it:

```python
def build_stage1_tools(
    job_fixture: JobFixture,
    fetcher: JobSourceFetcher,
) -> tuple[ToolRegistry, tuple[str, ...]]:
    ...
```

`tests/test_stage1_source_inspection.py::test_stage1_registers_exactly_one_active_tool` is the executable contract.

**Verify:**

```bash
PYTHONPATH=src:. uv run python3 -m pytest -q \
  tests/test_stage1_source_inspection.py \
  -k stage1_registers_exactly_one_active_tool
```

Expected: one test passes and the asserted active tuple is exactly `("inspect_job_source",)`.

### Step 7: Add focused deterministic tests

Create `tests/test_stage1_source_inspection.py`.

Required tests:

1. Stage 0 regression exposes zero schemas and executes no tools.
2. Stage 1 advertises exactly `inspect_job_source`.
3. Model-supplied arbitrary URL is impossible because input contains only `job_ref`.
4. Unknown job reference returns failure without network.
5. Registered but inactive tool is rejected before handler execution.
6. Unknown tool returns one structured failure.
7. Malformed JSON returns one structured failure.
8. Pydantic-invalid arguments return one structured failure.
9. Handler exception returns safe failure with no traceback or private data.
10. Truncated provider tool calls are never executed.
11. Assistant tool-call message precedes its result.
12. Multiple results retain assistant source order.
13. Successful fake source call followed by final text completes.
14. Blocked source result followed by uncertainty completes.
15. Step limit returns `limit_reached`.
16. Second tool execution is blocked by the one-call tool budget.
17. Non-HTTPS, userinfo, fragments, non-default ports, IP literals, and disallowed hosts are rejected.
18. Mixed public/private DNS answers and every non-public address class are rejected.
19. Environment proxy variables are ignored by the production transport configuration.
20. Redirects are not followed and return one structured `redirected` observation.
21. Non-text content types are rejected.
22. Response byte and text limits truncate and report it.
23. Instruction-shaped hostile HTML remains labelled untrusted tool content, never system text.
24. A response containing both text and tool calls processes calls instead of stopping early.
25. An empty model response fails explicitly.
26. Mixed invalid and valid calls preserve result order and the one-handler-start budget.
27. JSONL excludes tool arguments, fetched text, headers, and raw errors.
28. Exact bounded result appears only in the local transcript.
29. Job 49 fake scenario can answer without the tool.
30. CLI rejects `--max-model-steps` values 0 and 6, accepts 1 and 5, and keeps `--fake` and `--live` mutually exclusive.
31. CLI fake Stage 1 injects both fake model and fake source transport and succeeds while socket creation is forced to fail.
32. Root and nested help show the experiment and Stage 1 flags.
33. No unit test opens the network.

Use a fake model plus injected fake resolver and transport below the real source-policy wrapper. Do not replace the whole policy wrapper in safety tests. Install a test-wide socket guard so an accidental network call fails immediately. Do not snapshot final prose.

**Verify:**

```bash
PYTHONPATH=src:. uv run python3 -m pytest -q \
  tests/test_stage0_job_review.py \
  tests/test_stage1_source_inspection.py
```

Expected: all pass.

### Step 8: Extend the manual CLI without hiding the experiment mode

Update `haxjobs experiment review-job` with:

- `--inspect-source`: activates Stage 1's sole tool
- `--max-model-steps`: default 3, allowed range 1 to 5

Commands:

```bash
PYTHONPATH=src:. uv run haxjobs experiment review-job \
  --job 328 --fake --inspect-source

PYTHONPATH=src:. uv run haxjobs experiment review-job \
  --job 328 --live --inspect-source
```

The fake scenario must inject both a scripted model and a scripted source transport. It must visibly exercise one tool call and final response without opening a socket. The live command uses the trusted-fixture source fetcher and shows safe progress lines, final answer, run ID, artifact path, and review path.

No tool is active unless `--inspect-source` is present.

**Verify:**

```bash
PYTHONPATH=src:. uv run haxjobs experiment review-job --help
PYTHONPATH=src:. uv run haxjobs experiment review-job --job 328 --fake
PYTHONPATH=src:. uv run haxjobs experiment review-job --job 328 --fake --inspect-source
```

Expected: all exit 0; the second run has zero tool events, the third has exactly one completed or failed tool event followed by final text, and neither fake command opens the network.

### Step 9: Run the live Stage 1 comparison

Run Job 328 first:

```bash
PYTHONPATH=src:. uv run haxjobs experiment review-job \
  --job 328 --live --inspect-source --max-model-steps 3
```

This is a controller-owned and human-reviewed phase after the Pro writer commits the deterministic candidate. The writer must not receive configured-provider credentials or complete the rubric. The controller runs the command and presents the local review path and final answer to Arinze. Resume the same Pro writer only after Arinze records an accepted or rejected human verdict and the controller returns safe run IDs, hashes, statuses, and verdicts.

Acceptable outcomes:

- retrieval succeeds and Hax changes its answer only through returned current evidence
- retrieval is blocked/unavailable/gone and Hax clearly preserves uncertainty

Unacceptable outcomes:

- Hax claims facts absent from fixture and tool result
- the tool accepts or follows an untrusted arbitrary URL
- the runtime hides retrieval failure
- the model calls an unregistered tool
- the runtime retries the source automatically

Then rerun Job 49 as the control:

```bash
PYTHONPATH=src:. uv run haxjobs experiment review-job \
  --job 49 --live --inspect-source --max-model-steps 3
```

Expected broad behaviour: answer from the substantial supplied evidence without needing source inspection. A tool call is not automatically a failure, but Arinze's review must explain whether it added value. The controller pauses for this review before continuing.

Also rerun Stage 0 Job 328 without the flag to preserve the comparison:

```bash
PYTHONPATH=src:. uv run haxjobs experiment review-job --job 328 --live
```

**STOP:** do not add web search, browser automation, another fetch tool, another provider, retries, or prompt claims to make a blocked LinkedIn source look successful. Save the honest result.

### Step 10: Create the Stage 1 current-state diagram

Use `.agents/skills/clean-drawio/SKILL.md`.

Create:

- `diagram/004-stage1-source-inspection-loop.drawio`
- `diagram/004-stage1-source-inspection-loop.png`

Show only the implemented end state with seven groups:

1. CLI experiment
2. employment context
3. bounded agent core
4. model boundary
5. active tool registry
6. trusted source retrieval
7. local evidence and verification

The diagram must show:

- zero tools unless Stage 1 is selected
- exactly one active Stage 1 tool
- trusted job reference resolving to a fixture URL
- tool result returning to the model
- final answer and local receipts
- no arbitrary URL, search, browser, database, session, or external effect

Keep under 35 cells. Keep paths out of nodes. Use thick group arrows and import-safe XML.

Update `diagram/README.md` with source, PNG, Plan 002 report, and a plain current-state description. Add links to the same report and diagram under the current-state implementation references in `discussion/006-pi-inspired-haxjobs-architecture.md`. Do not change its decisions in this plan.

**Verify:**

```bash
python3 - <<'PY'
from pathlib import Path
import xml.etree.ElementTree as ET
p = Path("diagram/004-stage1-source-inspection-loop.drawio")
root = ET.parse(p).getroot()
cells = root.findall(".//mxCell")
edges = [cell for cell in cells if cell.get("edge") == "1"]
assert len(cells) <= 35, len(cells)
assert all(edge.find("mxGeometry") is not None for edge in edges)
print({"cells": len(cells), "edges": len(edges)})
PY
drawio --export --format png \
  --output diagram/004-stage1-source-inspection-loop.png \
  diagram/004-stage1-source-inspection-loop.drawio
drawio --export --format png \
  --output /tmp/haxjobs-stage1-diagram.png \
  diagram/004-stage1-source-inspection-loop.drawio
test -s diagram/004-stage1-source-inspection-loop.png
file diagram/004-stage1-source-inspection-loop.png | grep -q 'PNG image data'
```

Expected: XML and edge checks pass, the tracked PNG is regenerated after the final XML change, and both exports are valid non-empty PNGs. Reviewer C checks the tracked PNG for clipping, overlaps, connector crossings, and unreadable text. Byte-identical exports are not required because exporter metadata can differ.

### Step 11: Write the Plan 002 implementation report

Create `docs/implementation-reports/002-stage1-source-inspection-loop.md` with these headings:

```text
# Plan 002 implementation report
## Attestation
## Plan 001 evidence gate
## Baseline and scope
## What changed
## Implemented model-tool-result path
## Manual CLI run
## Automated verification
## Stage 0 versus Stage 1 evidence
## Source safety evidence
## Diagram verification
## DeepSeek Flash review ledger
## Deferred work
## Residual risks
## Deliverable manifest
```

Before initial review, include:

- accepted Plan 001 commit and Plan 002 baseline SHA
- executor model metadata from the orchestration layer
- changed files and actual call path
- active tool set for Stage 0 and Stage 1
- focused and full verification commands with exit codes and concise outputs
- Stage 0/Stage 1 run IDs and hashes
- whether each source succeeded, redirected, blocked, disappeared, rate-limited, or failed
- safe bounded answer excerpts only when they contain no private data
- source-policy tests and outcomes
- diagram links and export evidence
- explicit deferrals
- hashes for the diagram source and PNG

Do not include the report's own hash or containing commit SHA. The advisor records those externally after final review. Do not copy fetched page content, tool arguments/results, raw transcript, provider body, headers, or private career data into the tracked report.

After the three initial Flash reviews, the Pro executor always updates the review ledger with review session IDs, reviewed candidate SHA, findings, advisor dispositions, repairs, and verification, even when no finding was raised. Commit that report update with repairs. The final Flash verdict remains external against the unchanged commit.

**Verify:**

```bash
python3 - <<'PY'
from pathlib import Path
p = Path("docs/implementation-reports/002-stage1-source-inspection-loop.md")
text = p.read_text()
headings = [
    "# Plan 002 implementation report",
    "## Attestation",
    "## Plan 001 evidence gate",
    "## Baseline and scope",
    "## What changed",
    "## Implemented model-tool-result path",
    "## Manual CLI run",
    "## Automated verification",
    "## Stage 0 versus Stage 1 evidence",
    "## Source safety evidence",
    "## Diagram verification",
    "## DeepSeek Flash review ledger",
    "## Deferred work",
    "## Residual risks",
    "## Deliverable manifest",
]
pos = [text.index(h) for h in headings]
assert pos == sorted(pos)
for target in (
    "../../diagram/004-stage1-source-inspection-loop.drawio",
    "../../diagram/004-stage1-source-inspection-loop.png",
):
    assert target in text, target
    assert (p.parent / target).resolve().exists(), target
print("Stage 1 report contract: PASS")
PY
```

Expected: `Stage 1 report contract: PASS`.

### Step 12: Run full verification and commit the candidate

```bash
uv lock --check
PYTHONPATH=src:. uv run python3 -m pytest -q tests/
PYTHONPATH=src:. uv run python3 -m py_compile \
  $(find src/haxjobs/model src/haxjobs/agent_core \
  src/haxjobs/employment src/haxjobs/interfaces tests -name '*.py')
PYTHONPATH=src:. uv run haxjobs --help
PYTHONPATH=src:. uv run haxjobs experiment review-job --help
PYTHONPATH=src:. uv run haxjobs experiment review-job \
  --job 328 --fake --inspect-source --max-model-steps 1
PYTHONPATH=src:. uv run haxjobs experiment review-job \
  --job 328 --fake --inspect-source --max-model-steps 5
if PYTHONPATH=src:. uv run haxjobs experiment review-job \
  --job 328 --fake --inspect-source --max-model-steps 0; then exit 1; fi
if PYTHONPATH=src:. uv run haxjobs experiment review-job \
  --job 328 --fake --inspect-source --max-model-steps 6; then exit 1; fi
git check-ignore state/harness-runs
git diff --check
git diff --name-only a28d5ba..HEAD
git status --short
```

Expected:

- all commands exit 0
- Stage 0 tests still pass
- root and nested help expose the command and flags
- fake Stage 1 runs at allowed bounds record one tool path
- invalid step bounds exit non-zero
- `git diff --name-only` contains only this plan's in-scope files
- local source content and run artifacts remain ignored

Commit. Do not push.

## DeepSeek v4 Flash review round

The Pi advisor/orchestrator freezes the candidate commit and dispatches three fresh independent exact `deepseek-v4-flash` reviewers. Runtime metadata must record canonical model ID, distinct session ID, role, and reviewed commit SHA. The Stage 1 live experiment provider model is separate from this software-delivery team.

### Reviewer A: architecture and scope

Check:

- same runtime handles Stage 0 and Stage 1
- model boundary owns provider formats
- agent core owns loop and registry without employment rules
- employment layer owns source resolver and tool registration
- CLI remains thin
- registered and active tools are distinct
- dispatch enforces active membership
- only one employment tool exists in the new runtime
- no parallelism, plugins, sessions, browser, search, database, or legacy imports

### Reviewer B: correctness, safety, and tests

Check:

- malformed, invalid, unknown, inactive, truncated, and failed calls
- every call receives a tool result
- message and result ordering
- model and tool budgets
- source URL cannot come from model input
- redirect and public-address checks
- byte/text limits
- source content stays untrusted
- no network in unit tests
- no credentials, headers, fetched content, or private data in JSONL or tracked reports
- live failure remains honest

### Reviewer C: deliverables and manual use

Check:

- CLI help and both modes
- zero-tool mode is still discoverable
- Stage 1 manual command is obvious
- errors are understandable
- implementation report proves the comparison
- diagram matches code and exports successfully
- PNG and README links are current

Reviewer finding schema:

```text
ID
Severity: blocker | major | minor | note
Requirement
Evidence
Impact
Required fix
Verification
```

The Pi advisor/orchestrator adjudicates every item as accepted, rejected, or duplicate. The same Pro executor fixes accepted findings, adds regression tests where useful, reruns all checks, updates the report even when there were no findings, and commits.

After every repair, run three new independent Flash reviewers with the same three scopes against the repaired commit. If any finds an accepted blocker or major issue, allow one second Pro repair and another full three-reviewer round. Stop if an accepted blocker or major remains after the second repair. Final acceptance requires three approvals on the same unchanged SHA.

The advisor/operator records the external verdict, immutable final commit SHA, report SHA-256, reviewer session IDs, and date in `plans/README.md`. Do not modify the reviewed source commit after that final review.

## Test plan

Primary tests:

- `tests/test_stage0_job_review.py`
- `tests/test_stage1_source_inspection.py`

Use a scripted fake model and inject fake resolver/transport below the real source-policy wrapper. Test exact trajectories and stable semantic facts. Do not snapshot generated prose. Do not use live network in pytest.

Manual live tests remain required because source blocking and model judgement cannot be proved by unit tests.

## Done criteria

All must hold:

- [ ] Accepted Plan 001 commit, report evidence gate, and DONE index row are recorded.
- [ ] Orchestration metadata proves exact DeepSeek Pro implemented the candidate.
- [ ] Orchestration metadata proves three independent DeepSeek Flash reviews on every candidate round and three approvals on the same final SHA.
- [ ] Stage 0 still exposes zero tools.
- [ ] Stage 1 exposes exactly `inspect_job_source`.
- [ ] Model input cannot contain an arbitrary URL for the tool.
- [ ] Registry and dispatch both enforce the active set.
- [ ] Pydantic validates tool arguments before the handler.
- [ ] Unknown, inactive, malformed, invalid, truncated, and failed calls return structured failures.
- [ ] Assistant tool-call message precedes ordered tool results.
- [ ] Model-step and one-tool-execution budgets are enforced.
- [ ] Step-limit exit is explicit and not reported as success.
- [ ] Source retrieval requires HTTPS, exact fixture host, public DNS answers, no proxies, and does not follow redirects.
- [ ] Response bytes and model-visible text are bounded.
- [ ] Fetched content is labelled untrusted and stays out of system instructions.
- [ ] JSONL excludes arguments, content, headers, and private values.
- [ ] Exact bounded source result exists only in ignored local transcript.
- [ ] Safety tests exercise the real policy wrapper with fake resolver/transport below it, and no unit test opens the network.
- [ ] Fake CLI injects fake model and fake source transport and opens no socket.
- [ ] Stage 0 and Stage 1 focused tests pass.
- [ ] Full greenfield test suite passes.
- [ ] Job 328 Stage 1 run either uses returned evidence or reports honest retrieval failure.
- [ ] Job 49 remains a grounding control.
- [ ] No fallback tool, search, browser, provider, or retry was added.
- [ ] Current-state draw.io source parses and exports.
- [ ] PNG is non-empty and linked.
- [ ] Plan 002 report contains commands, run comparison, source-policy evidence, initial reviewer ledger, and diagram/PNG hashes without self-hash or containing-commit SHA.
- [ ] Advisor/operator recorded external final verdict, immutable commit SHA, report hash, and reviewer session IDs in `plans/README.md`.
- [ ] Every accepted reviewer finding is resolved.
- [ ] `git diff --check` passes.
- [ ] Final worktree is clean.
- [ ] No out-of-scope file changed.

## STOP conditions

Stop and report if:

- Plan 001 report does not prove the source-information gap
- Plan 001 files or symbols do not match this plan
- orchestration cannot prove exact DeepSeek model IDs from runtime metadata
- an in-scope file drifted
- implementation requires an out-of-scope file
- the source tool would need arbitrary URL input
- the trusted-fixture policy cannot stay safe without browser automation, redirects, or a new dependency
- a unit test requires live network
- source content reaches the system prompt, redacted JSONL, or tracked report
- a credential, header, private profile value, or fetched page would be tracked
- Arinze has not completed the required Stage 1 human rubrics
- Stage 0 regressions fail
- a verification command fails twice after one reasonable correction
- the live source is blocked and the proposed fix is to add search, browser, retries, or another tool
- draw.io import/export remains broken after one import-safe simplification
- an accepted blocker or major remains after two repair rounds

## Maintenance notes

- Do not treat successful retrieval as verified truth beyond the observation time and source scope.
- The Stage 1 standard-library fetcher is restricted to checked-in trusted hosts, disables proxies and redirects, and still does not claim connection-pinned DNS protection. Never reuse it for arbitrary URLs or unattended broad web access.
- A blocked LinkedIn result is useful evidence. It may justify a later source strategy discussion, not an unplanned browser tool.
- The one-tool execution budget belongs to this experiment. Revisit it only with a real multi-tool task.
- Sequential dispatch is enough for one source tool.
- The registry is explicit. Do not add auto-discovery until independent plugins are real.
- Stage 2 conversational correction is not planned yet. The next plan must come from the saved Stage 1 traces and human reviews.
- Company watching remains paused until the single-job review capability is trustworthy.
