---
status: decided
created: 2026-07-17
scope: Choose the language, framework floor, observability floor, and verification floor for the first Hax experiment
builds_on:
  - discussion/004-minimal-job-native-harness.md
research_date: 2026-07-17
---

# Implementation stack, observability, and verification

## Decisions carried forward

The first harness experiment is now decided:

- freeze one truthful backend-career fixture from the user's real evidence
- run Job 49 first as the clear-evidence control
- run Job 328 second as the missing-evidence stress case
- Stage 0 has no tools
- Stage 1 adds only `inspect_job_source(job_ref)`

Before code, we need to choose enough of the implementation stack to make those experiments useful and repeatable.

We do not need the final cloud architecture. We need a good first foundation that does not trap HaxJobs later.

# Short recommendation

Use:

```text
Python for Hax and all career product logic
Pydantic for model-facing and trust-boundary contracts
plain Python for the first run loop
one real provider adapter plus one fake adapter
pytest for deterministic checks
local redacted JSONL for agent traces
Python logging for normal diagnostics
Markdown rubrics for human review
uv for environment and dependency locking
TypeScript later for the web interface only
```

Do not add an agent framework, telemetry server, workflow engine, eval platform, Go service, or Rust service for Stage 0.

The first framework we should reconsider is PydanticAI. The first trace UI we should reconsider is Phoenix. The first durable workflow system we should reconsider is Temporal. Each has a concrete activation condition below.

# First, observability and verification are different

These terms get mixed together a lot.

## Observability

Observability answers:

> What happened inside this run?

For example:

- which instructions Hax received
- which career and job fixtures were selected
- which model was called
- how long it took
- what the model returned
- which tools it requested
- what each tool returned
- why the run stopped
- token usage and provider errors

It is the flight recorder.

## Verification

Verification answers:

> Was what happened acceptable and useful?

For example:

- did Hax identify Job 49 as IT support?
- did it keep sponsorship unknown?
- did it invent details for Job 328?
- did a fake model's malformed tool arguments get rejected?
- did the run stop at the step limit?
- did Hax make a clear recommendation?

It is the inspection after the flight.

We need both from the first experiment, but neither requires a platform.

# Language choice

## Recommendation: Python

Python gives HaxJobs the best combined fit for:

- model provider SDKs
- typed model and tool contracts through Pydantic
- evaluation libraries
- HTTP, HTML, PDF, data, and browser work
- SQLite in the standard library
- CLI development
- FastAPI later
- the user's existing experience
- fast iteration while the product is still being discovered

The harness mostly waits on model calls, web pages, browsers, and storage. Rust or Go speed would not make those remote systems answer faster.

## Comparison

| Question | Python | TypeScript | Go | Rust |
|---|---|---|---|---|
| Major model SDK support | Excellent | Excellent | Good | Thin, often REST or community clients |
| Agent and evaluation libraries | Strongest current choice | Strong and improving | Limited | Limited |
| Runtime validation for model data | Pydantic is a very good fit | Zod is a very good fit | More manual glue | Strong types, more schema plumbing |
| Static web and document processing | Excellent | Good | Good | More work |
| Browser automation | Official Playwright support | Best native Playwright experience | Community binding | Community binding |
| Async network work | Good enough | Very good | Excellent | Excellent |
| CPU and memory performance | Weakest | Fine | Strong | Strongest |
| Native single-binary packaging | Awkward | Improving | Excellent | Excellent |
| Speed for one developer building this product | Best fit | Close second | Slower | Slowest |
| Later React interface | Separate API boundary | Same language | Separate API boundary | Separate API boundary |

## Why TypeScript is the real alternative

TypeScript has a serious case:

- the web interface is already React and TypeScript
- Playwright starts in the Node world
- Zod gives good runtime validation
- OpenAI, Anthropic, and Gemini support TypeScript well
- one language can reduce mental switching

But the one-language benefit is smaller than it looks. The browser interface and agent runtime still have different trust boundaries, dependencies, release cycles, and data access. We need runtime validation across that boundary anyway.

HaxJobs' centre is model work, research, document processing, evaluation, and career data. Python wins that combination.

Use TypeScript later as a thin interface over the same Python actions. Do not rewrite career logic in the browser or Node server.

## Why not Go now

Go would give us:

- easy native binaries
- simple deployment
- cheap concurrency
- predictable resource usage

It loses on:

- agent and evaluation library depth
- research and document tooling
- model-specific experimentation speed
- the amount of glue needed around structured outputs and tests

Go becomes interesting if discovery later needs thousands of concurrent fetches and profiling shows Python is the actual limit. That would justify a small fetch worker, not a rewrite of Hax.

## Why not Rust now

Rust would give us:

- strong memory and concurrency checks
- fast, small native programs
- good control over resources

It would also make every experiment slower to write and change. The main HaxJobs risks are bad permissions, false claims, private-data leakage, prompt injection, stale sources, and external actions without approval. Rust does not solve those.

Rust becomes interesting for a constrained native component, untrusted local execution, or a hard resource target. None of those exists in Stage 0.

# Exact Python floor

## Python version

Use a currently supported Python version that all selected dependencies support. Python 3.12 is the conservative floor. Python 3.13 is fine if the live dependency check is clean.

Do not make a language-version decision from fashion. Pin the version after the Stage 0 dependency check.

## Environment and packaging

Use `uv` because the repository already uses it and it handles:

- Python versions
- virtual environments
- locked dependencies
- running tools
- package installation

No Poetry, Conda, pip-tools, or second package manager.

## CLI

Use the standard library's `argparse` for the experiment runner unless the command shape becomes painful.

One command does not justify Typer or Click. Reconsider Typer when the real CLI has enough nested product commands that help text and typed option handling remove meaningful code.

# Framework choice

## Recommendation: plain Python plus Pydantic contracts

The first loop is small:

```python
messages = build_context(fixture)
response = model.complete(messages)
save_trace(response)
return response.text
```

Stage 1 adds a bounded loop:

```python
for step in range(max_steps):
    response = model.complete(messages, tools=allowed_tools)
    record_model_response(response)

    if not response.tool_calls:
        return response.text

    messages.append(response.as_assistant_message())
    for call in response.tool_calls:
        result = dispatch(call)
        messages.append(result.as_tool_message())
```

That does not need LangChain, LangGraph, PydanticAI, or the OpenAI Agents SDK yet.

Pydantic should validate:

- normalized model responses
- tool arguments
- tool results
- fixture records
- trace events
- later product actions at trust boundaries

Pydantic is a contract library here. It is not the architecture.

## Why not PydanticAI from the first line

PydanticAI is the strongest framework candidate for HaxJobs. It already has:

- typed dependencies and outputs
- broad model support
- message history
- toolsets
- deferred tools and approvals
- fake and function models for tests
- OpenTelemetry instrumentation
- multi-agent patterns
- Temporal integration

That is exactly why we should keep it nearby.

But Stage 0 is supposed to expose the real primitive. If we begin inside a framework, we may learn the framework's message types and lifecycle before we learn what HaxJobs itself needs.

Start plain. Switch when PydanticAI can delete tested plumbing rather than merely replacing ten obvious lines with its own vocabulary.

### PydanticAI activation condition

Reconsider it when the local loop has accumulated several of these:

- provider normalization
- streaming
- retry handling
- usage limits
- deferred approval continuation
- message processors
- toolset composition
- tracing instrumentation
- substantial fake-model plumbing

The test is simple:

> Would PydanticAI remove meaningful code while preserving HaxJobs-owned state, policy, and product actions?

If yes, use it. If it only makes the code look more agent-like, do not.

## OpenAI Agents SDK

Good parts:

- compact agent and runner model
- tools, handoffs, sessions, guardrails, and tracing
- strong OpenAI Responses support
- multiple-provider routes exist

Costs:

- OpenAI concepts remain the centre
- hosted tracing creates privacy and provider coupling
- server-managed conversation and compaction can become hidden application state
- HaxJobs would inherit provider-shaped choices too early

Use it only if OpenAI Responses becomes an intentional primary platform and its realtime, hosted traces, handoffs, or server-managed state are product requirements.

HaxJobs currently uses DeepSeek. That makes an OpenAI-centred framework a strange default.

## LangChain

LangChain is useful when an application needs many provider, retriever, and middleware integrations.

HaxJobs Stage 0 needs one model call. Stage 1 needs one tool. LangChain would add more concepts than it removes.

Reconsider only when we would otherwise rebuild several valuable LangChain integrations or middleware pieces.

## LangGraph

LangGraph is for explicit state machines with:

- branches and joins
- checkpointing
- pause and resume
- human input between nodes
- replay and state inspection
- subgraphs

That may fit later application, research, or company-watch operations. It does not fit a one-job review yet.

Reconsider when HaxJobs has a real workflow that must visibly branch and resume across restarts.

## Temporal

Temporal is not an agent loop. It is an outer system for durable work.

It becomes useful when:

- a watch sleeps for days
- the process or machine can restart
- an approval can arrive later
- retries must survive crashes
- the exact operation history matters
- multiple workers execute bounded attempts

That maps well to the standing commitments discussed earlier. Still, adding Temporal before one watch exists would mean operating a server to schedule nothing.

Reconsider when the first standing commitment must survive process or host failure.

## Prefect

Prefect is a lighter Python choice for scheduled data work, retries, and an operator UI.

It may fit discovery pipelines if the main need is running and observing scheduled Python work. Temporal is stronger when durable waits, approvals, and exact recovery are correctness requirements.

Do not choose between them until the first real long-running operation exists.

## Hermes

Hermes remains a pattern library, not a runtime dependency.

Useful patterns to copy in small form:

- stable, contextual, and volatile prompt layers
- head and recent-tail preservation during compaction
- tool-result size limits
- cancellation
- isolated sub-agent context
- SQLite session search when needed

Do not import Hermes' gateway, terminal, browser, messaging, memory, provider fallback, and broad tool assumptions into HaxJobs.

# Model provider boundary

## One normalized boundary

HaxJobs should own a small interface such as:

```python
class ModelClient(Protocol):
    def complete(self, request: ModelRequest) -> ModelResponse:
        ...
```

`ModelResponse` needs enough information for the run loop:

- assistant text
- tool calls
- usage when returned
- provider stop reason
- provider model ID
- raw provider payload or safe reference for debugging

## Do not flatten providers too aggressively

Providers differ in:

- reasoning items
- tool-call representation
- conversation continuation
- prompt caching
- compaction
- structured-output support
- usage reporting

The common interface should support HaxJobs without pretending the providers are identical. Provider-specific options can live in the adapter.

## First provider

Use the already configured real provider for Stage 0. Do not add fallback routing.

Add one scripted fake that implements the same interface. The fake is more important than a second real provider because it lets us test malformed tool calls, errors, limits, and exact trajectories without network cost.

# Observability floor

## Recommendation: two local records

### 1. Normal application log

Use Python `logging` for:

- warnings
- exceptions
- component name
- run ID
- timing summaries
- local diagnostics

Do not put full prompts, CVs, profiles, credentials, or fetched pages into logs.

### 2. Agent event trace

Use append-only JSONL for the experiment's structured events.

One line is one event. A small trace may look like:

```json
{"type":"run_started","run_id":"run_123","fixture":"job-49"}
{"type":"context_built","run_id":"run_123","manifest_hash":"..."}
{"type":"model_completed","run_id":"run_123","model":"...","duration_ms":2800}
{"type":"run_completed","run_id":"run_123","stop_reason":"final_answer"}
```

The real schema should include:

- schema version
- event, run, turn, span, and parent IDs
- timestamp and duration
- event type
- outcome and safe error code
- provider and exact model
- instruction and fixture hashes
- tool name and bounded safe result metadata later
- usage and cost when available
- stop reason

## Context manifest

Do not save only the final prompt string.

Save identifiers and hashes for:

- application revision
- instruction version
- flow-prompt version
- model and settings
- tool schema version
- fixture versions
- selected career-context version
- redaction-policy version

That lets us explain why two runs differed without copying all private content into one trace file.

## Privacy rule

Employment traces can contain names, addresses, work history, salary, immigration details, private documents, and provider credentials.

Default rules:

- no secrets
- no authorization headers
- no raw CV or complete profile
- no arbitrary fetched-page dump
- use IDs and hashes where possible
- use bounded excerpts only in explicit local debug mode
- redact before writing, not only before later export
- sanitize any failure before turning it into a checked-in test fixture

The trace store could become the biggest private-data leak in the application if we treat logging as harmless.

# Why not OpenTelemetry now

OpenTelemetry gives standard traces, metrics, logs, context propagation, collectors, and many backends.

Stage 0 has one local process and one model call. Installing an SDK and collector would not teach us more than a clear JSONL record.

Shape the local events so they can later map to spans:

- run or agent span
- model span
- tool span
- policy span
- evaluator span

Add OpenTelemetry when the CLI, API, worker, or background operations cross process boundaries and we need one trace across them.

# OpenInference

OpenInference defines AI-specific span names and fields on top of OpenTelemetry, including model, agent, tool, retriever, guardrail, and evaluator spans.

Use it as vocabulary now. Do not bind business objects to its schema or install instrumentation in Stage 0.

If we later add an OpenTelemetry backend, map our trace events to the useful OpenInference parts.

# Trace and evaluation platforms

## Phoenix

Phoenix is the first platform to test if JSONL becomes annoying because it is:

- open source
- free to self-host
- able to run without sending data to Arize
- based on OpenTelemetry and OpenInference
- built for model and tool traces
- able to manage datasets and experiments

Activation condition:

- nested tool runs are hard to inspect in files
- the fixture set becomes a maintained eval dataset
- experiment comparison is recurring work
- more than one reviewer needs searchable traces

Do not deploy it before that.

## Langfuse

Langfuse has strong traces, prompt versions, datasets, experiments, and self-hosting.

Its current full self-hosted setup includes several services such as the web app, worker, Postgres, ClickHouse, Redis or Valkey, and blob storage. That is far too much for Stage 0.

Reconsider for a collaborative production setup when its prompt and evaluation workflow justifies the operations.

## MLflow

MLflow is open source, self-hostable, OpenTelemetry-compatible, and has tracing, evaluation, feedback, and prompt management.

It is a broader ML platform than the first Hax experiment needs. Reconsider if HaxJobs later wants one open platform across model experiments, prompts, traces, and evaluation.

## Logfire, LangSmith, and Braintrust

These can be useful managed products, but their strongest setup routes create hosted or paid self-hosting dependencies.

HaxJobs is local-first and handles private career data. They are not first choices without a deliberate data-hosting and procurement decision.

# Verification floor

## Layer 1: code checks with a fake model

Use pytest to prove deterministic behaviour:

- context ordering
- fixture loading
- source labels
- trace creation
- stop limits
- unknown tool rejection
- malformed argument rejection
- tool result ordering
- no network use in unit tests
- redaction rules

The fake model should be scriptable:

```python
fake = FakeModel([
    ToolCall(name="inspect_job_source", arguments={"job_ref": "job-328"}),
    FinalText("I still cannot verify enough detail to recommend this role."),
])
```

This verifies the surrounding software without asking whether a live model happens to cooperate today.

## Layer 2: fixture behaviour checks

Check stable facts, not exact prose.

Job 49 examples:

- recommendation is negative
- role family is understood as IT support
- sponsorship remains unknown
- cited reasons come from the supplied job evidence

Job 328 examples:

- evidence is marked insufficient before source inspection
- no hidden old-evaluation claims appear
- the next useful check is source inspection

Do not snapshot the full answer. Natural language will vary and exact snapshots will fail for harmless wording changes.

## Layer 3: human rubric

A person reads the live answer and records:

- grounded or invented
- clear or vague
- useful recommendation or fence-sitting
- natural Hax voice or generic report
- correct handling of unknowns
- any harmful or misleading advice

For Stage 0, the user and developer are the same person, so this can be one short Markdown review per run.

## Layer 4: later model grader

A model grader may later help score qualities such as clarity, groundedness, or tone across many cases.

It must not become the release authority for:

- factual correctness
- consent
- external actions
- private-data handling
- evidence provenance

Model judges have position and style biases. If we add one, pin the judge model and rubric, compare against human labels, shuffle answer order for pairwise tests, and keep disagreement visible.

# Evaluation tools

## pytest

Use now. It handles the deterministic floor and already fits Python.

## promptfoo

Useful later for:

- comparing several prompts or models
- deterministic tool-use assertions
- red-team matrices
- latency and cost comparisons

It adds Node tooling. Add it only when the comparison matrix becomes painful in pytest.

## DeepEval

Useful for ready-made model-graded metrics. Most interesting metrics still depend on a judge model.

Do not add it until one specific metric has been checked against HaxJobs human labels.

## Inspect AI

Useful for serious agent evaluations, sandboxed tasks, rich logs, datasets, and scorers.

It is a good later option for adversarial or long-running capability tests. It is too much for two initial job fixtures.

## Pydantic Evals

Worth reconsidering with PydanticAI or once our fixture evaluation code starts becoming its own small framework. Plain pytest is enough first.

# Recommended first stack

```text
Runtime:          Python 3.12 or 3.13, pinned after dependency check
Environment:      uv
Contracts:        Pydantic v2
Agent loop:       plain Python
Provider:         current configured provider through one local adapter
Test model:       one scripted fake adapter
CLI:              argparse
HTTP later:       ordinary bounded HTTP client
Storage Stage 0:  local JSONL run artifacts
Diagnostics:      Python logging
Verification:     pytest + fixture checks + Markdown human rubric
Web UI later:     React + TypeScript calling Python product actions
```

# Activation table

| Observed need | Add or reconsider |
|---|---|
| Loop plumbing becomes a maintained subsystem | PydanticAI |
| OpenAI becomes the deliberate main platform | OpenAI Agents SDK |
| Explicit branched workflows need checkpoint, pause, resume, and replay | LangGraph |
| Standing commitments must survive host failure and wait for days | Temporal |
| Main need is scheduled Python pipelines with an operator UI | Prefect |
| Local JSONL is painful to inspect or compare | Phoenix |
| CLI, API, and worker need one cross-process trace | OpenTelemetry |
| Prompt and model comparison matrix outgrows pytest | promptfoo or Pydantic Evals |
| Adversarial long-horizon agent tests need sandboxes and rich transcripts | Inspect AI |
| Python is proven to bottleneck high-volume source fetching | A small Go fetch service |
| Constrained native or untrusted execution becomes real | A narrow Rust component |

# Main tradeoff in the recommendation

Owning the first loop means we write and test some plumbing ourselves.

The benefit is that we see exactly how instructions, context, tools, traces, and stops work. That matters because HaxJobs is supposed to be a job-native agent system, not an application hidden inside another agent framework.

The cost stays acceptable only while the loop remains small. We should not become emotionally attached to custom code. If PydanticAI later removes a growing pile of provider and lifecycle plumbing without taking ownership of HaxJobs policy or state, switching is the lazy and correct move.

# Research sources

Primary references used for this decision:

- [OpenAI API libraries](https://developers.openai.com/api/docs/libraries)
- [Anthropic client SDKs](https://docs.anthropic.com/en/api/client-sdks)
- [Gemini API libraries](https://ai.google.dev/gemini-api/docs/libraries)
- [Python asyncio](https://docs.python.org/3/library/asyncio.html)
- [Python sqlite3](https://docs.python.org/3/library/sqlite3.html)
- [Pydantic JSON Schema](https://pydantic.dev/docs/validation/latest/api/pydantic/json_schema/)
- [PydanticAI testing](https://pydantic.dev/docs/ai/guides/testing/)
- [PydanticAI deferred tools](https://pydantic.dev/docs/ai/tools-toolsets/deferred-tools/)
- [PydanticAI Temporal integration](https://pydantic.dev/docs/ai/integrations/durable_execution/temporal/)
- [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/)
- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- [Temporal Python SDK](https://docs.temporal.io/develop/python)
- [Prefect interactive workflows](https://docs.prefect.io/v3/advanced/interactive)
- [OpenTelemetry sensitive-data guidance](https://opentelemetry.io/docs/security/handling-sensitive-data/)
- [OpenTelemetry GenAI conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/)
- [OpenInference specification](https://arize-ai.github.io/openinference/spec/)
- [Phoenix self-hosting](https://arize.com/docs/phoenix/self-hosting)
- [Langfuse self-hosting](https://langfuse.com/self-hosting)
- [MLflow tracing](https://mlflow.org/docs/latest/genai/tracing/)
- [Promptfoo deterministic assertions](https://www.promptfoo.dev/docs/configuration/expected-outputs/deterministic/)
- [Inspect AI evaluation logs](https://inspect.aisi.org.uk/eval-logs.html)

# Questions for Arinze

1. **Language split:** Decided. Python owns Hax and career logic. TypeScript is reserved for the later interface.
2. **Framework floor:** Decided. Stage 0 and Stage 1 use plain Python plus Pydantic. PydanticAI is the first framework to reconsider when it can delete meaningful loop code.
3. **Evidence stack:** Decided. The first experiments use local redacted JSONL, Python logging, pytest, and Markdown human review, with no telemetry or evaluation server.

# Decision ledger

| Item | Status | Current direction |
|---|---|---|
| Core language | Decided | Python. |
| Later web language | Decided | TypeScript as an interface only. |
| Environment | Decided | `uv`. |
| Contract library | Decided | Pydantic v2. |
| First run loop | Decided | Plain Python. |
| First provider strategy | Working recommendation | One configured provider plus one scripted fake. |
| CLI | Working recommendation | `argparse` until command complexity justifies more. |
| Stage 0 traces | Decided | Local redacted JSONL plus Python logging. |
| Stage 0 verification | Decided | pytest, fixture checks, and Markdown human review. |
| First framework to reconsider | Working recommendation | PydanticAI. |
| First trace UI to reconsider | Working recommendation | Phoenix. |
| Durable workflow system | Deferred | Compare Temporal and Prefect when a standing commitment must survive process failure. |
| Go or Rust | Deferred | Add only as narrow measured components, not Hax's core. |
