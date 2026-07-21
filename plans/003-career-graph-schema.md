# Plan 003: Career Graph and First Real Conversation

| Key | Value |
|-----|-------|
| **Plan ID** | 003 |
| **Title** | Career Graph and First Real Conversation |
| **Correction baseline** | `7bd9a55` |
| **Design baseline** | `7da5786` |
| **Previous delivery** | Career graph landed at `9ee53be`, Plan index update at `e907b1b` |
| **Depends on** | Plan 001 DONE, Plan 002 DONE |
| **Status** | REOPENED, corrected after the rejected Textual TUI |
| **Priority** | P1, make the career graph usable through Hax |

---

## Executor warning

This plan is not final just because it is written down.

Before editing code, compare every instruction against the live repository. Read the source, tests, imports, and current dependency lock. If the plan disagrees with working code, stop and report the drift. Do not silently adapt. Do not preserve stale behavior through compatibility wrappers.

The writer must read these files first:

1. `AGENTS.md`
2. `discussion/research/2026-07-17-interactive-agent-cli-study.md`
3. `discussion/research/2026-07-17-pi-hermes-job-native-harness-study.md`
4. `discussion/006-pi-inspired-haxjobs-architecture.md`
5. `docs/harness-primitives/00-How-An-Agent-Actually-Runs.md`
6. `docs/harness-primitives/02-context-delivery-and-management.md`
7. this plan in full

---

## Purpose

Plan 003 originally delivered the career graph correctly, then attached the wrong interface to it.

The rejected interface was a Textual profile browser, followed by two fake chat shells. Those implementations treated the terminal as an app that owned behavior. HaxJobs needs the opposite boundary: the terminal submits input to a real session and renders events produced by the runtime.

The corrected Plan 003 keeps the delivered career graph and adds the smallest real conversational path over it:

```text
inline terminal
    -> employment session
    -> domain-free turn runtime
    -> model and tool loop
    -> employment context and actions
    -> career graph
```

At the end, running `haxjobs` opens an inline conversation with Hax. Responses come from the configured provider. The terminal can stream text, show real tool lifecycle events, interrupt work, persist canonical history, and resume a prior session.

No fake response is allowed in the live interface.

---

## Corrected scope

### Accepted history, verify but do not rebuild

The following work already exists and remains part of Plan 003:

| Delivered phase | Live files |
|-----------------|------------|
| Career models | `src/haxjobs/employment/schema.py` |
| SQLite career store | `src/haxjobs/employment/store.py` |
| One-way fixture migration | `src/haxjobs/employment/migration.py` |
| Profile CLI | `src/haxjobs/interfaces/profile_cli.py`, `src/haxjobs/cli.py` |
| Career graph tests | `tests/test_career_graph.py` |
| Career graph artifacts | `deliverables/003-career-graph/` |

These files may only change if the new conversation path exposes a real defect that blocks the accepted behavior. Any such change must be explained in the completion report and covered by a focused regression test.

### Rejected history, never restore

Delete nothing further because the rejected implementation is already gone.

Do not restore:

- `src/haxjobs/interfaces/tui.py`
- Textual
- full-screen alternate-buffer UI
- profile tables, trees, cards, panels, headers, or footers
- message bubbles, avatars, or fake typing indicators
- fake Hax replies in live mode
- terminal code that reads `CareerStore`
- terminal code that builds prompts
- terminal code that calls the provider or dispatches tools

### New work

The corrected work has seven pieces:

1. canonical conversation messages
2. content-bearing live interaction events
3. streaming and cancellation in the model boundary
4. an append-only session store
5. a bounded streaming model and tool turn runtime
6. employment context assembly from `CareerStore`
7. a small inline `prompt_toolkit` terminal client

---

## Architecture rules

These rules are release gates.

### Layer ownership

```text
TerminalClient
    owns editing, key bindings, display, and nothing else

EmploymentSession
    owns prompt boundaries, subscribers, cancellation, queue policy,
    canonical history, persistence, and resume

Turn runtime
    owns the bounded model -> tool -> model loop

EmploymentHost
    owns Hax instructions, selected career context, and active employment tools

CareerStore and employment actions
    own durable career facts and job-search behavior
```

### Import rules

- `interfaces/terminal.py` must not import `CareerStore`, provider clients, job fixtures, `ToolRegistry`, or employment handlers.
- `agent_core/session.py` must not import `prompt_toolkit` or employment modules.
- `agent_core/turn.py` must remain domain-free. No job, CV, company, track, application, or evidence names.
- `employment/host.py` may import `CareerStore`, employment tools, and agent-core protocols.
- one composition root creates the provider, career store, employment host, session store, and session.
- `RunEvent` remains safe redacted telemetry. Live interface events use a separate type.

### State ownership

- session history stores conversation messages and tool messages.
- career facts stay in `CareerStore` and are selected again for each turn.
- provider request objects are disposable projections, not durable truth.
- terminal display state is never durable product state.

### Cancellation

Escape must cause a real session abort.

The session sets a cancellation signal. The provider stream and current tool task observe it. The turn records an interrupted outcome and returns to a promptable state. Hiding output while work continues is not cancellation.

### Fake model boundary

The fake model exists only for tests and an explicit `--fake` development option. Every fake response must be scripted by the test or caller. The terminal must never invent assistant content, tool progress, or completion text.

---

## Phase 0: Preflight and drift record

**Files changed:** none

1. Confirm `git status --short` is clean.
2. Confirm `git rev-parse HEAD` matches the approved execution baseline.
3. Run the current suite and record the exact count.
4. Confirm `src/haxjobs/interfaces/tui.py` is absent.
5. Confirm `textual` is absent from `pyproject.toml` and `uv.lock`.
6. Inspect all callers of `ModelClient.complete()`, `run_stage0()`, `ToolRegistry.dispatch()`, and `CareerStore` before changing shared behavior.
7. Record any drift in the implementation report before editing.

STOP if the worktree is dirty for reasons not created by the executor.

---

## Phase 1: Canonical conversation messages

### Goal

Create the provider-neutral messages a session can persist and replay.

### Files

- Create: `src/haxjobs/agent_core/messages.py`
- Modify: `src/haxjobs/agent_core/types.py`
- Create: `tests/test_conversation_messages.py`

### Contract

Use strict Pydantic models with `extra="forbid"`:

```text
UserMessage
    kind = "user"
    message_id
    turn_id
    content
    created_at

AssistantMessage
    kind = "assistant"
    message_id
    turn_id
    content
    status = "complete" | "interrupted" | "failed"
    created_at

ToolCallMessage
    kind = "tool_call"
    message_id
    turn_id
    call_id
    tool_name
    arguments
    created_at

ToolResultMessage
    kind = "tool_result"
    message_id
    turn_id
    call_id
    tool_name
    ok
    result
    error_code
    error
    created_at
```

Provide:

```python
ConversationMessage = UserMessage | AssistantMessage | ToolCallMessage | ToolResultMessage

def project_messages(
    system_prompt: str,
    context_messages: list[ModelMessage],
    history: list[ConversationMessage],
) -> list[ModelMessage]:
    ...
```

Projection rules:

- system prompt first
- turn-scoped career context second
- canonical session history after that
- assistant tool calls project to provider assistant messages with tool calls
- tool results project to provider tool messages with matching call IDs
- career context is never appended to canonical history
- model-specific raw response objects are never stored

Remove the unused `AgentMessage` class from `agent_core/types.py` if no live caller remains. Do not keep a compatibility alias.

### Tests

Write failing tests first for:

- strict validation
- JSON round trip for every message type
- correct provider projection order
- matching tool call and tool result IDs
- career context present in projection but absent from persisted history

---

## Phase 2: Live interaction events

### Goal

Give trusted interfaces enough information to render real work without weakening redacted telemetry.

### Files

- Create: `src/haxjobs/agent_core/live_events.py`
- Create: `tests/test_live_events.py`

### Contract

Define a strict `LiveEvent` model and enum:

```text
session_started
user_message_accepted
turn_started
assistant_started
assistant_delta
assistant_completed
tool_requested
tool_started
tool_progress
tool_completed
tool_failed
turn_interrupted
turn_failed
turn_completed
session_settled
```

Common fields:

```text
session_id
turn_id
event_type
timestamp
```

Optional event-specific fields:

```text
text
delta
call_id
tool_name
tool_status
tool_duration_ms
error_code
error
```

Rules:

- `LiveEvent` may carry assistant text needed by the local terminal.
- `RunEvent` in `agent_core/events.py` remains unchanged and content-free.
- `LiveEvent` is not a subclass of `RunEvent`.
- subscriber failures are collected or logged and never change the turn result.
- no event may carry provider credentials, HTTP headers, or provider request objects.
- `tool_progress` is emitted only when a tool supplies real progress. The terminal never fabricates it.

### Tests

Write failing tests first for:

- every event type validates
- extra fields are rejected
- deltas preserve exact order
- subscriber failure does not break delivery to other subscribers
- live events and telemetry events remain separate

---

## Phase 3: Streaming model boundary

### Goal

Stream real provider output while keeping the accepted non-streaming experiment path working.

### Files

- Modify: `src/haxjobs/model/types.py`
- Modify: `src/haxjobs/model/client.py`
- Modify: `src/haxjobs/model/fake.py`
- Create: `tests/test_model_streaming.py`

### Contract

Add provider-neutral stream events:

```text
text_delta
complete_tool_call
response_completed
response_failed
```

A complete tool call contains the final accumulated `call_id`, tool name, and raw JSON arguments. Provider chunk assembly belongs in the provider adapter, not in the turn runtime.

Extend `ModelClient`:

```python
class ModelClient(Protocol):
    async def complete(self, request: ModelRequest) -> ModelResponse | ModelFailure:
        ...

    def stream(
        self,
        request: ModelRequest,
        cancel_event: asyncio.Event,
    ) -> AsyncIterator[ModelStreamEvent]:
        ...
```

`OpenAIModelClient.stream()` must:

- call the OpenAI-compatible API with `stream=True`
- yield text deltas as received
- accumulate fragmented tool-call names and arguments by provider call index
- yield only complete internal tool calls
- yield provider usage and finish reason at completion when available
- stop and close the provider stream when cancellation is set
- return a safe failure event without leaking credentials or raw headers
- use no automatic SDK retries

`FakeModelClient.stream()` must:

- accept explicit scripted stream sequences
- record every `ModelRequest`
- yield only scripted events
- support an optional per-event delay for cancellation tests
- stop when cancellation is set
- fail loudly when scripted turns are exhausted

Keep `complete()` intact for Stage 0 and Stage 1 experiments. Do not implement one path as a wrapper around the other unless tests prove identical semantics.

### Tests

No live provider calls.

Write failing tests first for:

- exact text delta order
- fragmented tool-call assembly using a mocked OpenAI stream
- cancellation stops future deltas
- safe provider failure
- existing `complete()` behavior unchanged

STOP if the installed OpenAI SDK cannot close or cancel the stream cleanly on Python 3.12.

---

## Phase 4: Append-only session persistence

### Goal

Persist canonical conversation history at durable boundaries and resume it after process exit.

### Files

- Create: `src/haxjobs/agent_core/session_store.py`
- Modify: `src/haxjobs/config.py`
- Create: `tests/test_session_store.py`

### Config

Add:

```python
SESSION_DB_PATH = Path(
    _env("HAXJOBS_SESSION_DB", str(STATE_DIR / "sessions.db"))
)
```

### Tables

```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    status TEXT NOT NULL,
    turn_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE session_messages (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    turn_id TEXT NOT NULL,
    message_kind TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
```

### Store API

```text
create_session(session_id)
get_session(session_id)
latest_session_id()
append_message(session_id, message)
load_messages(session_id)
mark_turn_settled(session_id, turn_count)
mark_session_closed(session_id)
```

Rules:

- plain stdlib `sqlite3`
- foreign keys on
- WAL only for file-backed databases, not `:memory:`
- append-only messages
- deterministic sequence order
- local DB file mode `0600`
- canonical tool calls and results are persisted because model replay needs them
- system prompts, career context snapshots, credentials, headers, and raw provider bodies are not persisted
- an interrupted partial assistant message is persisted with status `interrupted`

### Tests

Write failing tests first for:

- session creation
- ordered message replay
- all message kinds round trip
- interrupted assistant message round trip
- latest session selection
- file mode `0600`
- foreign key enforcement

---

## Phase 5: Bounded streaming turn runtime

### Goal

Run one conversational turn through a domain-free model and tool loop.

### Files

- Create: `src/haxjobs/agent_core/turn.py`
- Modify only if required: `src/haxjobs/agent_core/tools.py`
- Create: `tests/test_turn_runtime.py`

### API

```python
async def run_turn(
    *,
    session_id: str,
    turn_id: str,
    model: ModelClient,
    system_prompt: str,
    context_messages: list[ModelMessage],
    history: list[ConversationMessage],
    tool_registry: ToolRegistry,
    active_tools: tuple[str, ...],
    cancel_event: asyncio.Event,
    emit: LiveEventEmitter,
    max_model_steps: int = 5,
) -> TurnResult:
    ...
```

### Required trajectory

```text
project canonical history and turn context
-> start provider stream
-> emit assistant deltas
-> collect completed tool calls
-> persistable assistant tool-call messages
-> dispatch only active registered tools
-> emit real tool lifecycle events
-> append canonical tool results
-> call the provider again
-> stop on final assistant response, cancellation, failure, or model-step limit
```

### Rules

- domain-free
- maximum five model steps
- tool arguments and outputs continue through Pydantic validation
- unknown, inactive, malformed, failed, and invalid-output tools become canonical tool results so the model can recover
- `tool_started` is emitted before dispatch
- `tool_completed` or `tool_failed` is emitted exactly once
- cancellation cancels the active provider task and tool task
- partial assistant text is returned with interrupted status
- no receipt writing inside this function
- no SQLite access inside this function
- no fake progress

Do not route the new product path through `run_stage0()`. That function remains the accepted experiment runner. Do not create a compatibility wrapper between the two runtimes.

### Tests

Write failing trajectory tests first for:

- text-only response
- model -> tool -> model response
- exact event ordering
- canonical tool call and result messages
- malformed arguments recover without a crash
- handler error recover without a crash
- model-step limit
- cancellation during text streaming
- cancellation while waiting for a tool task
- provider failure after partial text

---

## Phase 6: Employment host and CareerStore context

### Goal

Connect the generic conversation runtime to real employment data without leaking domain logic into the session or terminal.

### Files

- Create: `src/haxjobs/employment/context.py`
- Create: `src/haxjobs/employment/host.py`
- Create: `tests/test_employment_host.py`

### Employment host protocol

Define the domain-neutral protocol in `agent_core/session.py` or a small `agent_core/host.py` only if needed by more than one module:

```text
system_prompt()
context_messages(history)
registered_tools()
active_tool_names(history)
```

The concrete employment implementation lives in `employment/host.py`.

### Career context selection

For v1:

- one person ID supplied at composition time
- one active track ID supplied at composition time, or the person's first track
- person name, location, work authorization, and notice period
- active track name and role families
- hierarchical skills with proficiency
- linked evidence needed to explain those skills
- skill gaps
- hard constraints
- preferences

Use three prompt tiers:

1. stable Hax identity and behavior
2. stable employment conversation instructions
3. volatile career context selected from `CareerStore`

The volatile career context is projected into the provider request for the current turn. It is not copied into session history.

The host must not read the private migration fixture. `CareerStore` is the source.

If the graph has no person or no track, return a typed setup error before calling the model. The terminal renders the error and tells the operator to run `haxjobs migrate`. Do not silently fall back to `CareerFixture`.

### One real employment action

Register the existing read-only `inspect_job_source(job_ref)` capability for trusted fixture job references 49 and 328.

Create the smallest trusted resolver inside the employment layer. The model supplies a `job_ref`, never a URL. The resolver maps that ref to a known saved fixture, then uses the existing `JobSourceFetcher` safety boundary.

The tool may be active on every employment conversation turn. The model decides whether the request needs it. No keyword intent parser in the terminal or session.

Do not add discovery, application generation, decisions, outreach, shell, filesystem access, or arbitrary URL fetching.

### Tests

Write failing tests first for:

- correct person and active track selection
- context contains only the selected track
- hierarchical skills and evidence are represented clearly
- hard constraints and preferences remain separate
- context changes when the active track changes
- missing profile returns a typed setup error without a model call
- trusted job refs resolve
- unknown job refs fail safely
- no arbitrary URL enters the tool schema
- the terminal and session never import `CareerStore`

---

## Phase 7: Employment session

### Goal

Own interaction boundaries, persistence, resume, subscribers, cancellation, and busy-input policy.

### Files

- Create: `src/haxjobs/agent_core/session.py`
- Create: `src/haxjobs/employment/composition.py`
- Create: `tests/test_session.py`

### Session API

```python
class AgentSession:
    async def prompt(self, text: str) -> TurnResult:
        ...

    def subscribe(self, listener: Callable[[LiveEvent], None]) -> Callable[[], None]:
        ...

    def abort(self) -> None:
        ...

    @classmethod
    def resume(..., session_id: str) -> AgentSession:
        ...
```

### Session behavior

1. persist the user message before any provider call
2. ask the host for current system prompt, context, and tools
3. freeze those inputs for the turn
4. call `run_turn()`
5. persist assistant, tool call, and tool result messages in emitted order
6. mark the turn settled before accepting the next normal prompt
7. emit `session_settled` on success, failure, limit, or interruption
8. resume by replaying canonical messages from `SessionStore`

### Busy-input policy

Start with one pending message slot:

- input submitted while busy becomes the pending message
- newer input replaces the existing pending message
- replacement is reported to the interface
- after the current turn settles, the pending message starts
- Escape interrupts the current turn, it does not delete the pending message

Do not build steering messages, multiple queues, priorities, background turns, or compaction.

### Composition root

`employment/composition.py` is the only place that creates:

- `OpenAIModelClient` or explicit fake client
- `CareerStore`
- employment host
- `SessionStore`
- `AgentSession`

The terminal receives an already constructed session.

### Tests

Write failing tests first for:

- first prompt persists before model invocation
- two turns replay prior canonical history
- resume after close
- subscriber event delivery
- abort returns the session to idle
- one pending message
- newer pending message replaces older one
- subscriber failure does not fail the turn
- no model call when career setup is missing

---

## Phase 8: Inline prompt_toolkit terminal

### Goal

Give the operator a real Pi-style conversation in normal terminal scrollback.

### Files

- Create: `src/haxjobs/interfaces/terminal.py`
- Modify: `src/haxjobs/cli.py`
- Modify: `src/haxjobs/__main__.py` only if required
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Create: `tests/test_terminal.py`

### Dependency

Add one direct dependency:

```toml
"prompt-toolkit>=3.0,<4.0"
```

Do not add Textual, Ink, Node, a web server, or another rendering framework.

### Commands

```text
haxjobs                     open or resume the latest live session
haxjobs chat                same behavior explicitly
haxjobs chat --new          create a new session
haxjobs chat --resume ID    resume a specific session
haxjobs chat --fake         explicit scripted development mode
```

Existing `profile`, `migrate`, and `experiment` commands remain available.

### Interaction contract

```text
Enter         submit
Shift+Enter   newline when the terminal reports the modified key distinctly
Ctrl+J        newline on every supported terminal
Escape        interrupt the active turn
Ctrl+C        clear a non-empty editor, exit when already empty and idle
Ctrl+D        exit when the editor is empty
```

Because terminals differ in how they encode Shift+Enter, Ctrl+J is the guaranteed multiline binding. Document any terminal-specific Shift+Enter limitation honestly.

### Rendering contract

- normal scrollback, `full_screen=False`
- no alternate screen
- prompt at the bottom
- user input stays visible after submission
- assistant deltas print as they arrive
- tool lifecycle lines are generated only from `LiveEvent`
- working status reflects runtime state but never pretends to be assistant text
- errors are safe and readable
- session ID and resume command are shown once
- terminal uses `prompt_toolkit.patch_stdout()` or its supported async equivalent so streaming output does not corrupt input
- terminal cleanup runs in `finally`

The terminal imports only the session protocol and live event types. It does not import employment storage, provider clients, or tool handlers.

### Tests

Use prompt_toolkit's test input and dummy output. No live provider calls.

Write failing tests first for:

- Enter submits once
- Ctrl+J inserts a newline
- Escape calls `session.abort()` only while busy
- Ctrl+C clear then exit behavior
- streamed assistant deltas render exactly once
- tool lifecycle lines come from actual events
- no response text exists outside event payloads
- `full_screen` is false
- cleanup runs after normal exit and simulated exception

Add one pseudo-terminal smoke test if the environment supports it. Skip with an explicit reason if the platform lacks PTY support. A skipped PTY test is not proof of Enter or interruption, so the prompt_toolkit input tests remain mandatory.

STOP if prompt_toolkit's async input cannot coexist with streamed output without deadlock or lost events. Do not replace it with `input()`.

---

## Phase 9: Documentation, manual proof, and deliverables

### Files

- Modify: `docs/GETTING_STARTED.md`
- Modify: `docs/PRODUCT.md` only if its current-state table is stale
- Modify: `plans/README.md`
- Update: `deliverables/003-career-graph/`

### Getting started

Document:

- installation
- migration prerequisite
- provider prerequisite
- `haxjobs` launch
- key bindings
- new and resumed sessions
- explicit fake mode
- current limitations
- commands that still exist

### Manual proof

Run with a disposable session database first:

```bash
HAXJOBS_SESSION_DB=/tmp/haxjobs-plan003-sessions.db uv run haxjobs chat --fake
```

Then run one live provider session using the operator's local config without printing credentials:

```bash
HAXJOBS_SESSION_DB=/tmp/haxjobs-plan003-live-sessions.db uv run haxjobs chat --new
```

Manually prove:

1. Enter submits.
2. Ctrl+J creates a multiline message.
3. assistant text streams from the model.
4. Escape interrupts an active turn.
5. a second turn includes prior history.
6. exit restores the shell.
7. resume loads prior canonical history.
8. asking about Job 328 can produce real `inspect_job_source` lifecycle events.

Do not record provider credentials, raw HTTP, private fixture contents, or full career context in deliverables.

### Deliverable folder

Plan 003 keeps one folder:

```text
deliverables/003-career-graph/
```

Required final contents:

```text
README.md
plan.md
report.md
career-graph-report.md
schema-diagram.drawio
schema-diagram.png
conversation-runtime.drawio
conversation-runtime.png
interaction-flow.drawio
interaction-flow.png
manual-proof.md
review-ledger.md
```

Before replacing the old report or diagram names, preserve the accepted career-graph artifacts under the explicit `career-graph-*` and `schema-diagram.*` names. This is artifact history, not a runtime compatibility layer.

The final `report.md` must cover the complete corrected Plan 003:

- accepted career graph work
- rejected TUI deletion
- new runtime and terminal work
- exact files changed
- exact tests and commands run
- manual proof
- known limitations
- deferred work
- final commit SHA

### Draw.io requirements

Create two new clean diagrams of the actual implemented system:

1. `conversation-runtime.drawio`: Terminal, Session, Turn Runtime, Model/Tools, Employment Host, CareerStore
2. `interaction-flow.drawio`: submit, persist, assemble context, stream, tool call, settle, resume

Follow `.agents/skills/clean-drawio/SKILL.md`:

- 5 to 7 groups
- no file paths inside nodes
- thick orthogonal arrows between groups
- no connector crossings where a lane order can avoid them
- valid import-safe XML
- real PNG exports
- visual inspection for clipping and overlap

---

## Files in scope

### Create

```text
src/haxjobs/agent_core/messages.py
src/haxjobs/agent_core/live_events.py
src/haxjobs/agent_core/session_store.py
src/haxjobs/agent_core/turn.py
src/haxjobs/agent_core/session.py
src/haxjobs/employment/context.py
src/haxjobs/employment/host.py
src/haxjobs/employment/composition.py
src/haxjobs/interfaces/terminal.py
tests/test_conversation_messages.py
tests/test_live_events.py
tests/test_model_streaming.py
tests/test_session_store.py
tests/test_turn_runtime.py
tests/test_employment_host.py
tests/test_session.py
tests/test_terminal.py
```

### Modify

```text
src/haxjobs/agent_core/types.py
src/haxjobs/model/types.py
src/haxjobs/model/client.py
src/haxjobs/model/fake.py
src/haxjobs/config.py
src/haxjobs/cli.py
pyproject.toml
uv.lock
docs/GETTING_STARTED.md
plans/README.md
deliverables/003-career-graph/*
```

### Modify only if a focused test proves it is required

```text
src/haxjobs/agent_core/tools.py
src/haxjobs/employment/job_source.py
src/haxjobs/employment/store.py
src/haxjobs/employment/review_job.py
src/haxjobs/employment/__init__.py
src/haxjobs/agent_core/__init__.py
```

### Do not touch

```text
state/
src/haxjobs/employment/migration.py
src/haxjobs/employment/schema.py
src/haxjobs/employment/fixtures.py
src/haxjobs/interfaces/profile_cli.py
src/haxjobs/interfaces/experiment_cli.py
tests/test_stage0_job_review.py
tests/test_stage1_source_inspection.py
tests/test_career_graph.py
```

Existing experiment files may only change if a shared protocol change makes them fail. If that happens, stop and report the exact conflict before editing them.

---

## Explicitly deferred

- context compaction
- token budgets
- branching conversations
- subagents inside Hax
- skills and saved workflows
- background operations
- scheduler work
- approval workflows
- external side effects
- discovery
- application generation
- outreach
- provider fallback
- model switching
- generic plugins
- MCP
- shell and filesystem tools
- web or desktop UI
- RPC mode
- multiple users
- database connection pools

Add these only after a real trace proves the need.

---

## Verification floor

Run from repository root:

```bash
PYTHONPATH=src:. uv run python3 -m pytest -q tests/test_conversation_messages.py
PYTHONPATH=src:. uv run python3 -m pytest -q tests/test_live_events.py
PYTHONPATH=src:. uv run python3 -m pytest -q tests/test_model_streaming.py
PYTHONPATH=src:. uv run python3 -m pytest -q tests/test_session_store.py
PYTHONPATH=src:. uv run python3 -m pytest -q tests/test_turn_runtime.py
PYTHONPATH=src:. uv run python3 -m pytest -q tests/test_employment_host.py
PYTHONPATH=src:. uv run python3 -m pytest -q tests/test_session.py
PYTHONPATH=src:. uv run python3 -m pytest -q tests/test_terminal.py
PYTHONPATH=src:. uv run python3 -m pytest -q tests/
PYTHONPATH=src:. uv run python3 -m py_compile $(find src tests -name '*.py')
uv lock --check
git diff --check
```

Also verify:

```bash
uv run haxjobs --help
uv run haxjobs chat --help
uv run haxjobs profile --help
uv run haxjobs experiment review-job --help
```

No test may call the real provider or modify the operator's normal session database.

---

## STOP conditions

STOP and report instead of guessing if:

1. the execution baseline differs from the approved clean commit
2. existing Stage 0, Stage 1, or career graph tests regress
3. the OpenAI SDK cannot stream and cancel cleanly
4. prompt_toolkit cannot preserve normal scrollback and async input
5. Escape cannot reach the active session while output is streaming
6. `CareerStore` cannot provide a useful selected-track context
7. a proposed shortcut requires terminal code to import provider, store, or tools
8. a tool cannot be cancelled honestly
9. private fixture data or credentials appear in events, logs, reports, or deliverables
10. implementation requires a new product decision not recorded here

Never add a fake shell to make the manual demo look complete.

---

## Execution and audit protocol

### Writer

Use one fresh DeepSeek V4 Pro writer in an isolated worktree.

The writer must:

- read the plan and live source before editing
- be the only source-code writer in that worktree
- use tests before non-trivial implementation
- commit the implementation
- produce the full deliverable folder
- report every command and result honestly

### Review round

Run at least four independent fresh DeepSeek V4 Pro reviewers against the same unchanged writer commit:

1. **Plan compliance and scope**
   - maps every corrected plan phase to code and tests
   - finds missing deliverables or unapproved scope

2. **Runtime correctness and cancellation**
   - inspects stream assembly, model/tool trajectory, event order, failure paths, abort, and busy input

3. **Persistence, privacy, and employment boundaries**
   - checks canonical replay, SQLite boundaries, file permissions, context selection, active tools, and import direction

4. **Terminal behavior, docs, diagrams, and manual proof**
   - checks Enter, multiline, Escape, scrollback, terminal restoration, report accuracy, and Draw.io artifacts

Reviewers are read-only. They must inspect the actual diff, run relevant checks, cite file and line evidence, and return APPROVED or NEEDS FIXES.

### Repair rounds

- one fresh DeepSeek V4 Pro writer applies only accepted findings
- run the full verification floor again
- run four new fresh DeepSeek V4 Pro reviewers against the repaired commit
- allow at most two repair rounds
- all final approvals must refer to the same unchanged commit
- remaining optional ideas are deferred, not used to keep the loop alive

### Merge gate

Do not apply the worktree commit to main until:

- the full suite passes
- manual interaction proof is complete
- diagrams parse, export, and pass visual review
- four DeepSeek V4 Pro reviewers approve the same commit
- the review ledger records findings and decisions
- main is still at the expected baseline or the plan has been reconciled again

---

## Deliverable report requirement

The executor must finish with an evidence-backed Markdown report covering:

1. what changed
2. how each layer connects
3. every file created or modified
4. tests written and exact results
5. manual commands and observed behavior
6. diagrams produced
7. reviewer findings and repairs
8. anything skipped or deferred
9. current risks and known limitations
10. the final commit SHA

A claim such as "streaming works" needs a test, trace, or manual proof. A pass-like sentence without command output or artifact evidence does not count.

---

## Corrected design decisions

| ID | Decision | Reason |
|----|----------|--------|
| D1 | Keep the delivered career graph | Its models, store, migration, CLI, and tests are valid foundation work. |
| D2 | Delete the Textual direction | It produced a profile app, not an agent interface. |
| D3 | Use normal terminal scrollback | This matches Pi, Hermes classic CLI, and Claude Code behavior. |
| D4 | Use prompt_toolkit only after the session works | The interface must sit on a real runtime. |
| D5 | Session owns canonical conversation history | Conversation state and career truth are different kinds of state. |
| D6 | CareerStore context is selected per turn | The model receives current relevant career facts without copying them into chat history. |
| D7 | Live events stay separate from telemetry | The terminal needs content while persistent telemetry stays redacted. |
| D8 | Provider adapter assembles stream chunks | Provider-specific chunk details do not belong in the agent loop. |
| D9 | The turn runtime remains domain-free | Employment behavior stays in the host and tools. |
| D10 | One pending message is enough for v1 | It proves busy-input behavior without building queue machinery. |
| D11 | Existing inspect_job_source is the first conversational tool | It is read-only, trusted-ref based, bounded, and already tested. |
| D12 | No compaction yet | Real session traces must show context pressure first. |

---

*Corrected after the Textual TUI was rejected. The career graph remains. The replacement is a real conversational runtime with a thin inline terminal over it.*
