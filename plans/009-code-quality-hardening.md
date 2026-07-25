# Plan 009 — Code Quality Hardening

> **Baseline:** `c2a4455` (v0.1.0 tag)
> **Drift stamp:** 2026-07-25
> **Status:** TODO
> **Depends on:** Plan 007 DONE (wheel must be clean before touching source)

## Goal

Reduce the three monolith files (turn.py, session.py, messages.py) into well-factored modules where each function does one thing, each module has a single responsibility, and the four-layer architecture boundary is enforced in `__init__.py` exports. No logic changes — this is structural refactoring with existing test coverage as the safety net.

---

## Current state — what's wrong

### `agent_core/turn.py` (1182 lines)

| Problem | Count |
|---|---|
| `TurnResult(...)` constructions | 22 (15 are near-identical 12-field blocks) |
| `return TurnResult(...)` exit paths | 14 different return points |
| Cancellation handling | Duplicated in 4 places (model stream cancel, RESPONSE_FAILED cancel, post-loop cancel check, external CancelledError) |
| Known anti-pattern | **Long Method** (refactoring.guru), **Repeated Code** |

Every exit path constructs the same 12-field TurnResult with only `exit_reason`, `safe_failure`, and `final_text` varying. Adding a field means touching 15+ locations.

### `agent_core/session.py` (696 lines)

| Problem | Count |
|---|---|
| `_settle_failed_turn()` duplicates settlement logic from `_run_turn()` | Full copy of measurement → settlement → event emission |
| `_run_turn()` handles 5 concerns in one method | User persistence, history loading, turn execution, persistence checking, settlement, event emission |
| Known anti-pattern | **Long Method**, **Duplicated Code** |

The two settlement paths (`_run_turn` success, `_settle_failed_turn`) implement identical measurement-record → mark-settled → emit-events logic but with different TurnResult construction.

### `agent_core/messages.py` (173 lines)

| Problem | Details |
|---|---|
| `project_messages()` uses `nonlocal` state machine | `pending_assistant_text`, `pending_tool_calls` mutated inside `_flush_pending()` closure |
| State machine has 4 message kind branches | user, assistant, tool_call, tool_result — each affects the accumulator differently |
| Known anti-pattern | **Mutable State in Closure** |

The code is correct but fragile to modify. Adding a new message kind requires understanding when the accumulator flushes.

---

## Architecture — what good looks like

The four-layer HaxJobs architecture is already correct:

```
interfaces/ → employment/ → agent_core/ → model/
```

The refactoring must preserve these rules:

1. `model/` imports nothing above it (only `config` and stdlib)
2. `agent_core/` imports only `model/` and stdlib — never `employment/`, never `interfaces/`
3. `employment/` imports `agent_core/` and `model/` — never `interfaces/`
4. `interfaces/` imports everything — CLI/terminal are the outermost layer
5. No circular imports
6. `__init__.py` in each package exports the public API, nothing leaks internals

---

## Scope

### In

- Extract `TurnResultBuilder` from turn.py
- Extract settlement logic from session.py into a shared helper
- Replace `project_messages()` closure state machine with a class
- Add `__all__` to every subpackage `__init__.py` to enforce the public API
- Add module-level docstrings explaining each file's single responsibility
- No logic changes — behavior must be byte-for-byte identical at the test level

### Out

- Changing any business logic, algorithm, or error handling
- Changing the CLI, model client, employment tools, or store
- New features
- Adding dependencies
- Changing `config.py`, `cli.py`, `setup_cli.py`, or any employment file

---

## Files

### Modify

- `src/haxjobs/agent_core/turn.py` — extract TurnResultBuilder, deduplicate exit paths
- `src/haxjobs/agent_core/session.py` — extract settlement helper, rename _settle_failed_turn to use shared path
- `src/haxjobs/agent_core/messages.py` — replace closure state machine with `MessageProjector` class
- `src/haxjobs/agent_core/__init__.py` — add `__all__`
- `src/haxjobs/model/__init__.py` — already has `__all__`
- `src/haxjobs/employment/__init__.py` — already has `__all__`
- `src/haxjobs/interfaces/__init__.py` — verify (currently empty, may not exist)

### Do not modify

- Any test files
- `config.py`, `cli.py`
- Any employment/ files (tools, job_actions, store, host, context, etc.)
- `model/client.py`, `model/types.py`, `model/fake.py`

---

## Phase 1: TurnResultBuilder

### Task 1: Add TurnResultBuilder to turn.py

**File:** `src/haxjobs/agent_core/turn.py`

Add a builder class after the `TurnResult` dataclass:

```python
class _TurnResultBuilder:
    """Mutable accumulator for TurnResult fields. Call .build() to get the frozen result."""

    def __init__(self, turn_id: str, user_message_id: str):
        self.turn_id = turn_id
        self.user_message_id = user_message_id
        self.exit_reason = TurnExitReason.COMPLETED
        self.final_text = ""
        self.model_steps = 0
        self.tool_starts = 0
        self.new_messages: list[ConversationMessage] = []
        self.safe_failure = ""
        self.model_name = ""
        self.provider_name = ""
        self.usage: ModelUsage | None = None
        self.input_characters = 0

    def build(self) -> TurnResult:
        return TurnResult(
            turn_id=self.turn_id,
            exit_reason=self.exit_reason,
            final_text=self.final_text,
            model_steps=self.model_steps,
            tool_starts=self.tool_starts,
            new_messages=list(self.new_messages),
            safe_failure=self.safe_failure,
            user_message_id=self.user_message_id,
            model_name=self.model_name,
            provider_name=self.provider_name,
            usage=self.usage,
            input_characters=self.input_characters,
        )

    def mark_interrupted(self) -> None:
        self.exit_reason = TurnExitReason.INTERRUPTED
        self.safe_failure = safe_error("interrupted")

    def mark_failed(self, reason: TurnExitReason, failure_key: str) -> None:
        self.exit_reason = reason
        self.safe_failure = safe_error(failure_key)
```

Replace every bare `TurnResult(...)` construction in `run_turn()` with builder usage. The 22 constructions become:

```python
# Before:
return TurnResult(
    turn_id=turn_id,
    exit_reason=TurnExitReason.PERSISTENCE_FAILED,
    final_text=accumulated_text,
    model_steps=model_steps,
    ...
)

# After:
builder.final_text = accumulated_text
builder.model_steps = model_steps
builder.tool_starts = tool_starts
builder.model_name = captured_model_name
builder.provider_name = captured_provider_name
builder.usage = captured_usage
builder.mark_failed(TurnExitReason.PERSISTENCE_FAILED, "assistant_persistence")
return builder.build()
```

The cancellation exit paths become:

```python
builder.mark_interrupted()
return builder.build()
```

### Task 2: Deduplicate cancellation exits

After introducing the builder, the 4 cancellation exit paths (model stream cancel, RESPONSE_FAILED cancel, post-loop check, external CancelledError) should all call a single helper:

```python
def _handle_cancellation(
    builder: _TurnResultBuilder,
    accumulated_text: str,
    persist_message: PersistCallback,
    emit: LiveEventEmitter,
    session_id: str,
    turn_id: str,
) -> TurnResult:
    builder.mark_interrupted()
    builder.final_text = accumulated_text
    if accumulated_text:
        # persist partial text, emit TURN_INTERRUPTED
        ...
    return builder.build()
```

### Task 3: Add module docstring

Replace the current module docstring with one that clearly states the single responsibility:

```python
"""Bounded streaming turn runtime — model-and-tool loop for one conversational turn.

Responsibilities:
- Stream model responses and handle text/tool-call events
- Dispatch tools through the ToolRegistry with cancellation safety
- Persist canonical messages at durable boundaries (tool-call before handler, tool-result after handler)
- Emit live events for each lifecycle transition
- Return a TurnResult with safe, content-free failure text

Does NOT:
- Own session state, history, or measurement (AgentSession in session.py owns those)
- Know about employment/career data
- Handle message projection (messages.py owns that)
"""
```

---

## Phase 2: Session settlement deduplication

### Task 4: Extract settlement helper

**File:** `src/haxjobs/agent_core/session.py`

Current: `_run_turn()` and `_settle_failed_turn()` each implement measurement → mark-settled → emit-events independently. The logic is identical except for the TurnResult construction.

Extract into a private helper:

```python
def _settle_turn(
    self,
    *,
    turn_id: str,
    started_at: str,
    started_mono: float,
    result: TurnResult,
    terminal_type: LiveEventType,
) -> TurnResult:
    """Persist measurement, mark turn settled, emit terminal events. Returns (possibly modified) result."""
```

Both `_run_turn()` and `_settle_failed_turn()` call this after constructing their TurnResult. The helper handles:
1. Record measurement — on failure, emit TURN_FAILED and return PERSISTENCE_FAILED result
2. Mark turn settled — on failure, emit TURN_FAILED and return PERSISTENCE_FAILED result
3. Emit terminal turn event
4. Emit SESSION_SETTLED

### Task 5: Factor `_run_turn()` into clear stages

Current `_run_turn()` does:

1. Persist user message
2. Emit SESSION_STARTED (once)
3. Emit USER_MESSAGE_ACCEPTED
4. Get system prompt, context, tools
5. Load canoncal history
6. Run turn
7. Handle persistence failure
8. Record measurement
9. Mark settled
10. Emit terminal events

After refactoring, stages 8-10 are in `_settle_turn()`. Stages 1-7 stay in `_run_turn()` but each is a separate code block with a clear comment. No extracted sub-functions needed for the 1-7 stages — they're already ~30 lines each and straightforward. The value is in removing the duplicated settlement logic.

---

## Phase 3: MessageProjector class

### Task 6: Replace closure state machine with class

**File:** `src/haxjobs/agent_core/messages.py`

Current:

```python
def project_messages(system_prompt, context_messages, history):
    pending_assistant_text = None
    pending_tool_calls = []

    def _flush_pending():
        nonlocal pending_assistant_text, pending_tool_calls
        ...
```

Replace with:

```python
class _MessageProjector:
    """Projects canonical conversation history to provider messages.

    Accumulates assistant text and tool calls, flushes on user/tool-result boundaries.
    """

    def __init__(self, system_prompt: str, context_messages: list[ModelMessage]):
        self._result: list[ModelMessage] = []
        self._pending_text: str | None = None
        self._pending_calls: list[dict] = []
        self._result.append(ModelMessage(role="system", content=system_prompt))
        self._result.extend(context_messages)

    def feed(self, msg: ConversationMessage) -> None:
        ...

    def finish(self) -> list[ModelMessage]:
        self._flush()
        return self._result

    def _flush(self) -> None:
        ...

def project_messages(
    system_prompt: str,
    context_messages: list[ModelMessage],
    history: list[ConversationMessage],
) -> list[ModelMessage]:
    projector = _MessageProjector(system_prompt, context_messages)
    for msg in history:
        projector.feed(msg)
    return projector.finish()
```

The `feed()` method replaces the for-loop body with 4 explicit branches. The class docstring documents the flush rules (flush on user message, on tool result, on finish). No `nonlocal` needed.

### Task 7: Add module docstring

```python
"""Canonical conversation messages — provider-neutral, persistable, replayable.

Responsibilities:
- Define the 4 canonical message types (User, Assistant, ToolCall, ToolResult)
- Project canonical history to provider-compatible ModelMessages
- Own the tool-call batching logic (assistant + tool_calls → one provider message)

Does NOT:
- Persist messages (session_store.py owns that)
- Know about streaming or model calls (turn.py owns that)
- Know about employment data
"""
```

---

## Phase 4: Enforce public API in __init__.py

### Task 8: Add `__all__` to agent_core/__init__.py

**File:** `src/haxjobs/agent_core/__init__.py`

Current:

```python
"""HaxJobs agent core — domain-free messages, tools, turn runtime, and session lifecycle."""

from haxjobs.agent_core.tools import EffectKind, ToolDefinition, ToolExecutionContext, ToolRegistry

__all__ = [
    "EffectKind",
    "ToolDefinition",
    "ToolExecutionContext",
    "ToolRegistry",
]
```

Add the session and messages exports that employment/ actually uses:

```python
from haxjobs.agent_core.messages import (
    ConversationMessage,
    AssistantMessage,
    ToolCallMessage,
    ToolResultMessage,
    UserMessage,
    project_messages,
)
from haxjobs.agent_core.session import AgentSession
from haxjobs.agent_core.session_store import SessionStore
from haxjobs.agent_core.turn import TurnResult, TurnExitReason, run_turn
from haxjobs.agent_core.live_events import LiveEvent, LiveEventType, LiveEventEmitter
from haxjobs.agent_core.errors import safe_error, safe_tool_error

__all__ = [
    # Tools
    "EffectKind",
    "ToolDefinition",
    "ToolExecutionContext",
    "ToolRegistry",
    # Messages
    "AssistantMessage",
    "ConversationMessage",
    "ToolCallMessage",
    "ToolResultMessage",
    "UserMessage",
    "project_messages",
    # Session
    "AgentSession",
    "SessionStore",
    # Turn
    "TurnResult",
    "TurnExitReason",
    "run_turn",
    # Events
    "LiveEvent",
    "LiveEventType",
    "LiveEventEmitter",
    # Errors
    "safe_error",
    "safe_tool_error",
]
```

### Task 9: Verify interfaces/__init__.py exists

If not, create it with appropriate exports or leave empty. The terminal, CLI, and setup_cli are entry points, not library APIs.

---

## Phase 5: Verification

### Task 10: Run tests after each phase

After Phase 1:
```bash
PYTHONPATH=src:. uv run -- python3 -m pytest -q tests/test_turn_runtime.py tests/test_conversation_messages.py tests/test_durable_tool_effects.py
```

After Phase 2:
```bash
PYTHONPATH=src:. uv run -- python3 -m pytest -q tests/test_session.py tests/test_session_store.py tests/test_terminal_pty.py
```

After Phase 3:
```bash
PYTHONPATH=src:. uv run -- python3 -m pytest -q tests/test_conversation_messages.py
```

After all phases:
```bash
PYTHONPATH=src:. uv run -- python3 -m pytest -q tests/    # must pass 290+
PYTHONPATH=src:. uv run -- python3 -m py_compile $(find src -name '*.py')
git diff --check
```

### Task 11: Test that agent_core never imports employment

```bash
grep -r "from haxjobs.employment\|from haxjobs\.employment\|import haxjobs.employment" src/haxjobs/agent_core/
```

Must produce no output.

---

## Stop conditions

- Any test fails or changes behavior
- Agent core imports employment (layer violation)
- TurnResult fields change meaning
- Messages project differently from before the refactor

---

## Deliverables

- `turn.py` with TurnResultBuilder, deduplicated cancellation, module docstring (~800 lines from 1182)
- `session.py` with shared settlement helper, clearer stage separation (~500 lines from 696)
- `messages.py` with MessageProjector class, no nonlocal state (~200 lines from 173)
- `agent_core/__init__.py` with complete `__all__`
- 290+ passing tests confirming byte-for-byte behavioral equivalence
