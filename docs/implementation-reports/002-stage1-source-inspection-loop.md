# Plan 002 implementation report

## Attestation

This report records the implementation of Plan 002 — the Stage 1 bounded source-inspection loop. Every verification command listed in the plan was run and passed, or its skip is stated. The implementation was executed on branch `advisor/002-stage1-source-inspection-loop` from the worktree at `/tmp/haxjobs-exec-002`.

## Plan 001 evidence gate

- **Plan 001 final SHA:** `a28d5ba` (Stage 0 observed job review, accepted)
- **Plan 001 report:** `deliverables/001-stage0/report.md`
- **Plan 001 diagram:** `diagram/003-stage0-observed-job-review.drawio` and `.png`
- **Plan 002 baseline SHA:** `422f771` (reconciled to `a28d5ba` — diff `a28d5ba..HEAD` is empty)

The Stage 0 evidence gap is demonstrated by the Job 328 fixture itself:
- `content_complete: false`
- `description_kind: title_and_url_stub`
- `source_status: lead_only`
- No responsibilities, requirements, employer description, or salary stored — only a title and LinkedIn URL stub.

The Plan 001 live experiment was deferred (no provider credentials were available), but the fixture data itself proves the need for source inspection.

## Baseline and scope

- **Plan 002 baseline:** `422f771` (clean reconciliation to `a28d5ba`)
- **Branch:** `advisor/002-stage1-source-inspection-loop`
- **Scope:** Extend Stage 0 runtime into a bounded tool-call loop with exactly one employment tool (`inspect_job_source`), trusted-fixture source retrieval, and full safety tests.

## What changed

### Changed files

| File | Change |
|---|---|
| `src/haxjobs/model/types.py` | Added `ToolSchema`, `ToolCall`, `tool_calls`/`tool_calls_unsafe` to `ModelResponse`, `tools` to `ModelRequest`, optional `tool_calls`/`tool_call_id` to `ModelMessage` |
| `src/haxjobs/model/client.py` | Map tool schemas to OpenAI format, map provider tool calls to internal `ToolCall`, preserve stop reason, mark length-truncated tool calls unsafe, exclude None from message dumps |
| `src/haxjobs/model/fake.py` | No changes needed — `ModelResponse` already carries `tool_calls` |
| `src/haxjobs/model/__init__.py` | Export `ToolCall`, `ToolSchema` |
| `src/haxjobs/agent_core/types.py` | Added `LIMIT_REACHED`, `EMPTY_MODEL_RESPONSE` exit reasons; `model_steps`, `tool_starts` to `RunResult` |
| `src/haxjobs/agent_core/events.py` | Added `TOOL_REQUESTED`, `TOOL_STARTED`, `TOOL_COMPLETED`, `TOOL_FAILED` event types; `call_id`, `tool_name`, `tool_status`, `tool_duration_ms`, `model_step` fields to `RunEvent` |
| `src/haxjobs/agent_core/runtime.py` | Extended `run_stage0` with bounded tool-call loop: active-tool schemas, dispatch, budget enforcement, event emission, transcript and provider message ordering |
| `src/haxjobs/agent_core/__init__.py` | Export `ToolDefinition`, `ToolRegistry` |
| `src/haxjobs/employment/fixtures.py` | Added `allowed_source_hosts` to `JobFixture` |
| `src/haxjobs/employment/review_job.py` | Added `_InspectJobSourceInput`, `_InspectJobSourceOutput`, `build_stage1_tools()` |
| `src/haxjobs/employment/__init__.py` | Export `JobSourceFetcher`, `SourceObservation`, `build_stage1_tools` |
| `src/haxjobs/interfaces/experiment_cli.py` | Stage 1 mode with `--inspect-source`, `--max-model-steps`, `_FakeSourceFetcher` for fake runs |
| `src/haxjobs/cli.py` | Added `--inspect-source`, `--max-model-steps` flags; `--fake`/`--live` mutual exclusion |
| `discussion/fixtures/harness/job-49.json` | Added `allowed_source_hosts: ["jobs.ashbyhq.com"]` |
| `discussion/fixtures/harness/job-328.json` | Added `allowed_source_hosts: ["uk.linkedin.com"]` |
| `tests/test_stage0_job_review.py` | Updated test_stage0_has_zero_tools → test_stage0_has_zero_tools_by_default |
| `discussion/006-pi-inspired-haxjobs-architecture.md` | Added current-state implementation references |
| `diagram/README.md` | Added entry for diagram 004 |

### New files

| File | Purpose |
|---|---|
| `src/haxjobs/agent_core/tools.py` | `ToolDefinition`, `ToolRegistry` — explicit tool registry with active-set enforcement |
| `src/haxjobs/employment/job_source.py` | `JobSourceFetcher`, `SourceObservation` — bounded trusted-fixture source retrieval with URL/DNS/content validation |
| `tests/test_stage1_source_inspection.py` | 35 deterministic tests covering tools, registry, runtime loop, source safety, CLI |
| `diagram/004-stage1-source-inspection-loop.drawio` | Stage 1 current-state diagram source |
| `diagram/004-stage1-source-inspection-loop.png` | Stage 1 diagram PNG export |
| `docs/implementation-reports/002-stage1-source-inspection-loop.md` | This report |

## Implemented model-tool-result path

```
CLI (haxjobs experiment review-job --job 328 --inspect-source)
  → experiment_cli.py: load career + job fixtures
  → employment/review_job.py:
       build_stage1_tools(job, fetcher) → (ToolRegistry, ("inspect_job_source",))
       assemble_job_review_request(career, job) → RunRequest
  → agent_core/runtime.py: run_stage0(request, model, tool_registry, active_tools)
       Loop:
        1. ModelRequest(messages, tools=[inspect_job_source schema])
        2. ModelClient.complete → ModelResponse(text, tool_calls=[...])
        3. ModelResponse has tool_calls:
           a. Preserve assistant message with tool_calls
           b. For each ToolCall in source order:
              - Emit tool_requested, tool_started events
              - ToolRegistry.dispatch(name, args, active_names)
              - If first valid handler start → consume budget
              - Append tool result to messages
              - Emit tool_completed or tool_failed event
           c. Loop back to model call
        4. ModelResponse has text, no tool calls → stop
       Exit: COMPLETED, LIMIT_REACHED, EMPTY_MODEL_RESPONSE, or MODEL_FAILED
  → Write 6 receipt files (events.jsonl, manifest.json, context.json,
      transcript.json, result.json, review.md)
```

Stage 0 (no `--inspect-source`):
```
→ run_stage0(request, model, active_tools=()) → one call, zero tool schemas
```

## Manual CLI run

### Stage 0 (zero tools)
```
$ haxjobs experiment review-job --job 328 --fake
FAKE_STAGE0_RESPONSE: provider boundary and artifact writing are working.
Run ID: f96a8d8f86d5
Model steps: 1
Tool starts: 0
Artifact directory: state/harness-runs/f96a8d8f86d5
```

### Stage 1 (one tool)
```
$ haxjobs experiment review-job --job 328 --fake --inspect-source
FAKE_STAGE1: one tool call completed, final response.
Run ID: 56d1b488b161
Model steps: 2
Tool starts: 1
Artifact directory: state/harness-runs/56d1b488b161
```

### Stage 1 bounds
```
$ haxjobs experiment review-job --job 328 --fake --inspect-source --max-model-steps 1
Run failed: limit reached after 1 model step(s)
Model steps: 1  Tool starts: 1

$ haxjobs experiment review-job --job 328 --fake --inspect-source --max-model-steps 0
Error: --max-model-steps must be between 1 and 5, got 0  (exit 2)

$ haxjobs experiment review-job --job 328 --fake --inspect-source --max-model-steps 6
Error: --max-model-steps must be between 1 and 5, got 6  (exit 2)
```

All exit codes and behaviors match the plan.

## Automated verification

| Command | Result |
|---|---|
| `uv lock --check` | PASS (exit 0) |
| `pytest -q tests/test_stage0_job_review.py` | 27 passed |
| `pytest -q tests/test_stage1_source_inspection.py` | 35 passed |
| `pytest -q tests/` | 62 passed |
| `py_compile $(find src/... tests -name '*.py')` | PASS (exit 0) |
| `haxjobs experiment review-job --help` | PASS, shows `--inspect-source` and `--max-model-steps` |
| `haxjobs experiment review-job --job 328 --fake` | PASS (exit 0, zero tools) |
| `haxjobs experiment review-job --job 328 --fake --inspect-source` | PASS (exit 0, one tool) |
| `haxjobs experiment review-job --job 328 --fake --inspect-source --max-model-steps 0` | PASS (exit 2) |
| `haxjobs experiment review-job --job 328 --fake --inspect-source --max-model-steps 6` | PASS (exit 2) |
| `git diff --check` | PASS (no output) |

## Stage 0 versus Stage 1 evidence

### Stage 0
- Active tools: `()` (empty)
- Tool schemas sent to model: none
- Model calls: exactly 1
- Tool starts: 0

### Stage 1
- Active tools: `("inspect_job_source",)`
- Tool schemas sent to model: exactly 1 (`inspect_job_source`)
- Model calls: 1 to N (default max 3)
- Tool starts: 0 to 1 (budget enforced)

### Job 49 vs Job 328

| | Job 49 (Trainline IT Support) | Job 328 (Oritain Software Engineer) |
|---|---|---|
| Evidence | Curated source summary | Title + URL stub |
| Content complete | false (truncated at 5000 chars) | false |
| Source status | direct | lead_only |
| Source URL | jobs.ashbyhq.com | uk.linkedin.com |
| Stage 0 answer | Can assess fit from stored evidence | Cannot assess — only title and URL |
| Stage 1 benefit | May not need tool (evidence sufficient) | Can retrieve current source content |

Live provider runs are deferred to the controller phase (Step 9) — no provider credentials were available during implementation.

## Source safety evidence

Safety tests in `tests/test_stage1_source_inspection.py`:

| Test | Coverage |
|---|---|
| `test_url_safety_rejections` | Non-HTTPS, userinfo, fragments, non-default ports, IP literals — all rejected |
| `test_disallowed_host_rejected` | Host not in `allowed_source_hosts` → `host_not_allowed` |
| `test_mixed_addresses_rejected` | Public + private DNS mix → rejected; all-public → accepted |
| `test_proxy_handler_disables_proxies` | `ProxyHandler({})` confirmed in production transport |
| `test_redirects_not_followed` | 302 → `redirected` observation, no follow |
| `test_non_text_content_type_rejected` | `application/pdf` → `unsupported_content_type` |
| `test_byte_and_text_limits` | 512KB byte cap, 12K char text cap, truncation flags set |
| `test_hostile_html_stays_in_tool_result` | Instruction-shaped HTML text remains in tool output, never system prompt |
| `test_handler_exception_returns_safe_failure` | Traceback/private data excluded from error envelope |
| `test_jsonl_excludes_tool_content` | Events contain no tool arguments or fetched text |
| `test_exact_result_only_in_transcript` | Full tool result in transcript.json, excluded from events.jsonl and manifest.json |

Socket guard: All 35 Stage 1 tests run with `socket.socket` patched to block `AF_INET`/`AF_INET6` creation. Tests use injected `resolver` and `transport_factory` instead.

## Diagram verification

- Source: `diagram/004-stage1-source-inspection-loop.drawio` — 35 cells, 7 edges
- PNG: `diagram/004-stage1-source-inspection-loop.png` — valid PNG, non-empty
- Groups: 7 (CLI Experiment, Employment Context, Bounded Agent Core, Model Boundary, Active Tool Registry, Trusted Source Retrieval, Local Evidence & Verification)
- Key elements shown: Stage 0 path (zero tools), Stage 1 loop, tool registry dispatch, trusted source retrieval (job_ref → fixture URL), no arbitrary URLs or external effects
- All 7 arrows have `mxGeometry`

## DeepSeek Flash review ledger

Not yet performed. Three independent `deepseek-v4-flash` reviews are pending per the plan. The ledger will be updated after the advisor dispatches reviewers.

| Round | Reviewer | Role | Session ID | Reviewed SHA | Findings | Disposition |
|---|---|---|---|---|---|---|
| 1 | TBD | Architecture/Scope | TBD | TBD | TBD | TBD |
| 1 | TBD | Correctness/Safety | TBD | TBD | TBD | TBD |
| 1 | TBD | Deliverables/Manual | TBD | TBD | TBD | TBD |

## Deferred work

- **Live Stage 1 run (Step 9):** Requires provider credentials (DeepSeek API key in `~/.haxjobs/haxjobs.toml`) and controller-owned career fixture. Both Job 328 and Job 49 live experiments are controller-owned.
- **Stage 2 conversational correction:** Not yet planned. Must emerge from Stage 1 traces and human reviews.
- **Multi-tool workflows:** Deferred. The one-tool execution budget belongs to this experiment.
- **Parallel dispatch:** Deferred. Sequential dispatch is sufficient for one source tool.
- **Auto-discovery registry:** Deferred. Explicit registration until independent plugins are real.
- **Company watching:** Remains paused until single-job review is trustworthy.
- **Connection-pinned DNS:** The standard-library fetcher does not pin DNS connections. This is a residual risk of the trusted-fixture experiment only — never reuse for arbitrary URLs.

## Residual risks

1. **Connection-pinned DNS not guaranteed:** The `urllib` transport may re-resolve below our wrapper. Acceptable for trusted-fixture scope only.
2. **Live provider untested:** The OpenAIModelClient adapter maps tool schemas and tool calls but has not been tested against a real DeepSeek endpoint.
3. **LinkedIn blocking is expected:** The source tool will likely return `blocked` or `unavailable` for LinkedIn URLs — this is valuable evidence, not a bug.
4. **No streaming:** Full response in one blocking call. Acceptable for Stage 1.
5. **Single handler start budget:** Only one tool handler execution is allowed. If the model requests inspect_job_source a second time, it gets `tool_budget_exhausted`.

## Deliverable manifest

| Path | Type | Status |
|---|---|---|
| `src/haxjobs/model/types.py` | Updated | ToolSchema, ToolCall, extended ModelMessage/ModelRequest/ModelResponse |
| `src/haxjobs/model/client.py` | Updated | Tool schema/call mapping, unsafe marker |
| `src/haxjobs/agent_core/tools.py` | New | ToolDefinition, ToolRegistry |
| `src/haxjobs/agent_core/types.py` | Updated | LIMIT_REACHED, EMPTY_MODEL_RESPONSE, model_steps, tool_starts |
| `src/haxjobs/agent_core/events.py` | Updated | 4 tool event types, tool metadata fields |
| `src/haxjobs/agent_core/runtime.py` | Updated | Bounded tool-call loop |
| `src/haxjobs/employment/job_source.py` | New | JobSourceFetcher, SourceObservation |
| `src/haxjobs/employment/review_job.py` | Updated | build_stage1_tools, tool I/O models |
| `src/haxjobs/employment/fixtures.py` | Updated | allowed_source_hosts on JobFixture |
| `src/haxjobs/interfaces/experiment_cli.py` | Updated | Stage 1 mode, FakeSourceFetcher |
| `src/haxjobs/cli.py` | Updated | --inspect-source, --max-model-steps |
| `tests/test_stage1_source_inspection.py` | New | 35 tests, no network |
| `tests/test_stage0_job_review.py` | Updated | 1 test updated for Stage 0 contract |
| `diagram/004-stage1-source-inspection-loop.drawio` | New | 35 cells, 7 edges |
| `diagram/004-stage1-source-inspection-loop.png` | New | Valid PNG export |
| `diagram/README.md` | Updated | Entry for diagram 004 |
| `discussion/006-pi-inspired-haxjobs-architecture.md` | Updated | Current-state implementation references |
| `discussion/fixtures/harness/job-49.json` | Updated | allowed_source_hosts |
| `discussion/fixtures/harness/job-328.json` | Updated | allowed_source_hosts |
