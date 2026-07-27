# Plan 010 — Model Layer Modular Architecture

> **Baseline:** `a30fae5` (latest main)
> **Drift stamp:** 2026-07-26
> **Status:** TODO
> **Depends on:** Plan 009 DONE

## Goal

Break the 300-line `model/client.py` monolith and the 1000-line `agent_core/turn.py` into focused modules. The model layer becomes a proper provider boundary with a DeepSeek-specific adapter that handles thinking mode, `reasoning_content` routing, context caching, and session isolation. The agent core separates message projection and tool dispatch from the agent loop. No logic changes — structural refactoring with existing test coverage as the safety net.

---

## Current state — what's wrong

### `model/client.py` (300 lines)

One class doing six things:

| Concern | Lines | Problem |
|---|---|---|
| Provider config loading | 36-56 | Mixed into adapter, reloads on every `_ensure_client()` call |
| OpenAI SDK client construction | 44-56 | No thinking mode, no `user_id`, no `reasoning_effort` |
| Non-stream `complete()` | 58-118 | Tool schema conversion duplicated from stream method |
| Stream handler | 120-230 | `reasoning_content` not captured, sent directly to model as unknowable deltas |
| Tool call accumulation | 180-220 | Good logic but sandwiched inside async stream handler — untestable in isolation |
| Error wrapping | 115-118, 228-233 | Bare `str(exc)` leaks provider internals into safe failure messages |

The streaming bug has a known root cause: when DeepSeek thinking mode returns `reasoning_content` chunks before `content` chunks, the current code ignores them (`delta.content` only). The model then receives incomplete tool-call trajectories because `reasoning_content` from tool-turns isn't preserved across requests.

### `model/types.py` — missing fields

`ModelStreamEventType` has `TEXT_DELTA` but no `THINKING_DELTA`. `ModelResponse` has no `reasoning_content` field. The stream event model cannot represent what DeepSeek actually sends.

### `agent_core/turn.py` — embedded concerns

The `run_turn()` function does message projection, tool dispatch, AND the agent loop in one function. `project_messages()` from `messages.py` is called once at loop entry but the reasoning-content preservation rule is never applied before sending messages to the model.

---

## Architecture — what good looks like

```
model/                              provider boundary. never imports agent_core or employment.
├── __init__.py                     re-exports
├── types.py                        unchanged but THINKING_DELTA added
├── errors.py                       unchanged (ModelFailure)
├── protocol.py                     ModelClient protocol (extracted from client.py)
├── schemas.py                      tool_schema_to_provider(), provider_to_internal_tool_call()
│
├── adapters/                       one adapter per provider family
│   ├── __init__.py
│   └── deepseek.py                 DeepSeekAdapter
│
├── streaming.py                    StreamAccumulator (extracted from client.py stream handler)
├── provider.py                     ProviderConfig — loads from haxjobs.toml
└── fake.py                         unchanged

agent_core/
├── turn.py                         agent loop only — thin 200-line orchestrator
├── dispatch.py                     tool dispatch (extracted from turn.py)
├── projection.py                   message projection (extracted from messages.py + turn.py)
└── ...
```

### Import rules (same as always)

1. `model/` imports nothing above it — only `config` and stdlib
2. `agent_core/` imports only `model/` and stdlib — never `employment/`, never `interfaces/`

### How the adapter pattern works

The `ModelClient` protocol stays unchanged. `DeepSeekAdapter` implements it and owns all DeepSeek-specific behavior:

```python
class DeepSeekAdapter:
    """DeepSeek API via OpenAI-compatible endpoint. Owns thinking mode."""

    def __init__(self, config: ProviderConfig):
        self._config = config
        self._client = AsyncOpenAI(api_key=config.api_key, base_url=config.base_url, max_retries=0)

    # Builds extra_body with thinking + reasoning_effort + user_id
    def _build_request_body(self, request: ModelRequest) -> dict: ...

    # Wraps stream, routes reasoning_content → THINKING_DELTA events
    async def stream(self, request, cancel_event) -> AsyncIterator[ModelStreamEvent]: ...

    # Non-stream path — same request body, collects reasoning_content into response
    async def complete(self, request) -> ModelResponse | ModelFailure: ...

    # Static helper: given a ConversationMessage list, preserve reasoning_content
    # on assistant messages that made tool calls. Called by projection layer.
    @staticmethod
    def requires_reasoning_content(message: ConversationMessage) -> bool: ...
```

### What StreamAccumulator does

Extracted from the async stream handler into a pure synchronous accumulator:

```python
class StreamAccumulator:
    """Collects stream deltas into finished events. Zero async. Testable in isolation."""

    def feed_text(self, text: str) -> list[ModelStreamEvent]: ...
    def feed_reasoning(self, text: str) -> list[ModelStreamEvent]: ...
    def feed_tool_call_delta(self, index: int, call_id: str, name: str, arguments: str) -> None: ...
    def flush_tool_calls(self, unsafe: bool = False) -> list[ModelStreamEvent]: ...
    def finalize(self, finish_reason: str, usage: ModelUsage | None) -> list[ModelStreamEvent]: ...
```

Each `feed_*` method returns zero or more `ModelStreamEvent` objects. No async, no openai types, no IO. The adapter passes deltas through it, the accumulator decides when tool calls are complete and when text/reasoning deltas should be emitted.

---

## Implementation phases

### Phase 1 — Model types and errors (no module splits yet)

**Files:**
- `model/types.py` — add `THINKING_DELTA` to `ModelStreamEventType`, add `reasoning_content: str = ""` to `ModelResponse`

**No new files.** Minimal change, zero risk.

**Tests:** Add one test verifying `THINKING_DELTA` event type serializes correctly.

---

### Phase 2 — Provider config extraction

**New file:**
- `model/provider.py` — `ProviderConfig` dataclass with `api_key`, `base_url`, `model`, `thinking_enabled (default True)`, `reasoning_effort (default "high")`, static `from_file(path)` classmethod

**Changed file:**
- `model/__init__.py` — add `ProviderConfig` to exports

**Deleted:** Nothing yet. Client still uses inline config loading.

**Tests:** Test `ProviderConfig.from_file()` with valid and missing TOML, default values, missing required keys.

---

### Phase 3 — Stream accumulator extraction

**New file:**
- `model/streaming.py` — `StreamAccumulator` class

**Changed file:**
- `model/__init__.py` — add `StreamAccumulator` to exports

**Tests:** 8-10 tests covering text delta feed, reasoning delta feed, tool call accumulation across multiple chunks, flush with unsafe flag, finalize with finish_reason and usage, empty accumulator edge cases.

This is the highest-value extraction because the accumulation logic is currently untestable in isolation (buried inside async stream handler).

---

### Phase 4 — Tool schema converter

**New file:**
- `model/schemas.py` — `tool_schemas_to_provider(tool_schemas) -> list[dict]`, `provider_tool_call_to_internal(raw_tool_call) -> ToolCall`

**Changed file:**
- `model/__init__.py` — add exports

**Tests:** Round-trip conversion test — ToolSchema list → provider format and back.

---

### Phase 5 — ModelClient protocol extraction

**New file:**
- `model/protocol.py` — `ModelClient` Protocol class (moved from `client.py`)

**Changed files:**
- `model/__init__.py` — import from protocol instead of client
- `model/client.py` — remove protocol definition, import from protocol

**Tests:** None needed (existing tests already test through the protocol).

---

### Phase 6 — DeepSeek adapter

**New file:**
- `model/adapters/__init__.py`
- `model/adapters/deepseek.py` — `DeepSeekAdapter` class

**Implementation details:**

1. Constructor takes `ProviderConfig`, creates `AsyncOpenAI` client
2. `_build_request_body(request)` — constructs the full API call dict including:
   - `model`, `messages`, `max_tokens`
   - `tools` via `schemas.tool_schemas_to_provider()`
   - `extra_body` with `thinking: {type: enabled}`, `reasoning_effort`, `user_id`
   - `stream_options: {include_usage: true}` when streaming
3. `stream(request, cancel_event)` — opens stream, feeds deltas through `StreamAccumulator`, yields events:
   - `content` deltas → `feed_text()` → `TEXT_DELTA` events
   - `reasoning_content` deltas → `feed_reasoning()` → `THINKING_DELTA` events
   - tool call deltas → `feed_tool_call_delta()` → `COMPLETE_TOOL_CALL` events on flush
   - `finish_reason` and `usage` → `finalize()` → `RESPONSE_COMPLETED` or partial flush with unsafe flag
4. `complete(request)` — non-streaming equivalent, collects `reasoning_content` from response into `ModelResponse.reasoning_content`
5. `reasoning_required_for_tool_turn(message)` — static check: if message is `ToolCallMessage` or an assistant message with `tool_calls` non-empty, return True

**Changed file:**
- `model/__init__.py` — add `DeepSeekAdapter` to exports

**Deleted:** Nothing yet. Old client still exists.

**Tests:**
- Adapter builds correct `extra_body` with thinking mode and user_id
- Stream yields `THINKING_DELTA` for reasoning_content chunks
- Stream correctly accumulates tool calls across multiple delta chunks
- Stream handles cancellation (cancel event set → RESPONSE_FAILED with "cancelled")
- `requires_reasoning_content()` returns True for tool-call messages, False for plain assistant messages
- Non-stream `complete()` populates `reasoning_content` field

---

### Phase 7 — Message projection with reasoning preservation

**New file:**
- `agent_core/projection.py` — `project_messages()` (moved from `messages.py`), `project_provider_messages()` (extracted from `turn.py` and `messages.py`)

**Key addition:** Before building the provider messages array, apply the reasoning-content preservation rule. For every `ToolCallMessage` in history, if the preceding assistant message had `reasoning_content`, copy it into the projected `ModelMessage` object.

**Implementation:**
```python
def project_messages(
    system_prompt: str,
    context_messages: list[ModelMessage],
    history: list[ConversationMessage],
) -> list[ModelMessage]:
    """Project internal messages into provider-ready ModelMessage list.
    
    Preserves reasoning_content on assistant messages that made tool calls
    (DeepSeek requires this for multi-turn thinking-mode conversations).
    """
    # ... existing projection logic ...
    # Apply reasoning preservation pass
    for i, msg in enumerate(result):
        if msg.role == "assistant" and msg.tool_calls:
            # Attach reasoning_content from original if present
            orig = history[i - 1] if i - 1 < len(history) else None  # adjusts for system prompt offset
            # ... reasoning_content copy logic ...
```

**Changed files:**
- `agent_core/messages.py` — delete `project_messages()` (it moves to projection.py), keep `AssistantMessage`, `UserMessage`, `ToolCallMessage`, `ToolResultMessage`, `ConversationMessage`, `MessageRole`
- `agent_core/turn.py` — import `project_messages` from `projection.py`
- `agent_core/__init__.py` — update exports

**Tests:**
- reasoning_content preserved when assistant message has tool calls
- reasoning_content not added when assistant message has no tool calls
- multi-turn conversation preserves reasoning across tool-call boundaries
- empty history handled correctly

---

### Phase 8 — Tool dispatch extraction

**New file:**
- `agent_core/dispatch.py` — `dispatch_tool_call()` function extracted from `turn.py`

**Extracts:** The 70-line tool dispatch block that validates arguments, calls `tool_registry.dispatch()`, persists the tool result, and appends to provider messages.

**Changed files:**
- `agent_core/turn.py` — import and call `dispatch_tool_call()`
- `agent_core/__init__.py` — add exports

**Tests:** Existing tests cover this path. Verify all pass.

---

### Phase 9 — Cleanup and deletion

**Deleted:**
- `model/client.py` — replaced by `protocol.py` + `adapters/deepseek.py`

**Changed files:**
- `agent_core/turn.py` — import from `model.adapters.deepseek` instead of `model.client`
- `agent_core/session.py` — same import change
- `model/__init__.py` — remove `OpenAIModelClient`, add `DeepSeekAdapter`

**Tests:** All existing tests must pass. Type-check all imports.

---

## Deliverables

- `model/provider.py` — ProviderConfig dataclass
- `model/protocol.py` — ModelClient protocol (extracted, no new logic)
- `model/streaming.py` — StreamAccumulator class
- `model/schemas.py` — tool schema conversion helpers
- `model/adapters/deepseek.py` — DeepSeekAdapter with thinking mode + reasoning_content
- `agent_core/projection.py` — message projection with reasoning preservation
- `agent_core/dispatch.py` — tool dispatch (extracted, no new logic)
- `model/client.py` — deleted
- Tests for all new modules
- Updated `model/__init__.py` and `agent_core/__init__.py` exports

## Out of scope

- Terminal UI changes (the TUI only renders events — it doesn't care about the adapter change)
- Employment layer tools (no new tools, no tool contract changes)
- Session store changes
- Provider credentials migration (haxjobs.toml structure unchanged)
- Anthropic API format adapter (DeepSeek only for v1)
- Retry logic (no retries yet, add when failures become common)

## Verification

```bash
PYTHONPATH=src:. uv run -- python3 -m pytest -q tests/
PYTHONPATH=src:. uv run -- python3 -m py_compile $(find src tests -name '*.py')
uv lock --check
git diff --check
```

**Live validation:** `haxjobs chat --new` with a simple message, verify streaming works without broken sentences.

**Files in scope:** model/*, agent_core/turn.py, agent_core/messages.py, agent_core/__init__.py, tests/

**Files NOT touched:** employment/*, interfaces/*, config.py, any CLI or terminal code

## STOP conditions

- Any test regression in the 290-test suite
- If `reasoning_content` preservation breaks multi-turn chat (live test with two messages where second depends on first)
- If stream events stop arriving during a live chat session
- Import cycle detected between model/ and agent_core/

---

> **Warning for executor:** This plan describes desired end state. Before implementing, compare every "Current state" claim against the live code at the current HEAD. If the code has already been partially refactored since this plan was written, adjust the phases accordingly. Do not blindly create modules that already exist or delete code that isn't there.
