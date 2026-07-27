# Plan 010 — Provider abstraction layer

> **Baseline:** `8f10995` (current main)
> **Drift stamp:** 2026-07-27
> **Status:** PENDING
> **Depends on:** Plan 009 DONE

## Goal

Replace the 300-line `model/client.py` monolith with a proper provider abstraction layer. The current file handles 6 concerns in one file: config loading, OpenAI SDK construction, non-stream completion, stream handling, tool call accumulation, and error wrapping. It's handcuffed to DeepSeek because `reasoning_content` has nowhere to live in the type system.

The replacement uses Pi's proven pattern: one generic adapter that reads a pure-data `ProviderProfile`, plus per-provider profile constants. Adding GPT 5.6 or Claude Opus later means one 8-line constant. Zero adapter changes. Zero agent loop changes.

This incidentally fixes the DeepSeek streaming bug — `thinking_format: "deepseek"` tells the adapter to capture `reasoning_content` chunks, and `requires_reasoning_preservation: true` carries them across tool turns.

---

## Architecture

```
model/
├── __init__.py
├── types.py              # +THINKING_DELTA event, +reasoning_content on ModelMessage + ModelResponse
├── protocol.py           # NEW — ModelClient protocol (complete + stream)
├── profiles.py           # NEW — ProviderProfile dataclass + detect_profile() + DEEPSEEK_PROFILE
├── adapter.py            # NEW — GenericAdapter implements ModelClient, reads profile flags
├── provider.py           # NEW — ProviderConfig from haxjobs.toml (extracted from old client.py)
├── schemas.py            # NEW — tool schema conversion
├── streaming.py          # NEW — StreamAccumulator (pure sync, testable in isolation)
└── fake.py               # unchanged
```

**Layer discipline:** Nothing in `model/` imports from `agent_core/`, `employment/`, or `interfaces/`. `agent_core/turn.py` imports `ModelClient` (protocol), `ProviderProfile`, `detect_profile`, `ProviderConfig`. `employment/composition.py` wires the concrete adapter.

---

## Phase 1 — Type system: reasoning_content + THINKING_DELTA

**File: `src/haxjobs/model/types.py`**

Add to `ModelStreamEventType` enum:

```python
THINKING_DELTA = "thinking_delta"
```

Add to `ModelResponse` dataclass:

```python
reasoning_content: str = ""
```

Add to `ModelMessage` dataclass:

```python
reasoning_content: str | None = None
```

All new fields default so existing JSON serializes/deserializes without migration.

**File: `src/haxjobs/agent_core/messages.py`**

Add to `AssistantMessage`:

```python
reasoning_content: str = ""
```

Default `""` means old session JSON without the field parses fine. `model_config.extra = "forbid"` accepts it because it's an explicit field.

---

## Phase 2 — ProviderProfile: pure-data flags

**File: `src/haxjobs/model/profiles.py`** (NEW)

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class ProviderProfile:
    """Pure-data flags describing a provider's behaviour.
    
    The adapter reads these flags. It never branches on provider name.
    Adding a new provider means one new constant. Zero code changes elsewhere.
    """
    thinking_format: str           # "disabled" | "deepseek" | "anthropic"
    max_tokens_field: str          # "max_tokens" | "max_completion_tokens"
    extra_body: dict               # e.g. {"thinking": {"type": "enabled"}} for DeepSeek
    reasoning_effort_field: str | None  # "reasoning_effort" or None
    requires_reasoning_preservation: bool  # carry reasoning_content across tool turns
    supports_stream_options: bool
    supports_json_mode: bool

# Provider constants
DEEPSEEK_PROFILE = ProviderProfile(
    thinking_format="deepseek",
    max_tokens_field="max_tokens",
    extra_body={"thinking": {"type": "enabled"}},
    reasoning_effort_field="reasoning_effort",
    requires_reasoning_preservation=True,
    supports_stream_options=True,
    supports_json_mode=True,
)

OPENAI_PROFILE = ProviderProfile(
    thinking_format="disabled",
    max_tokens_field="max_completion_tokens",
    extra_body={},
    reasoning_effort_field="reasoning_effort",
    requires_reasoning_preservation=False,
    supports_stream_options=True,
    supports_json_mode=True,
)

DEFAULT_PROFILE = ProviderProfile(
    thinking_format="disabled",
    max_tokens_field="max_completion_tokens",
    extra_body={},
    reasoning_effort_field=None,
    requires_reasoning_preservation=False,
    supports_stream_options=True,
    supports_json_mode=False,
)

def detect_profile(provider: str, base_url: str) -> ProviderProfile:
    """Auto-detect profile from provider name and base URL.
    
    Falls back to DEFAULT_PROFILE if unknown. Users can override by passing
    an explicit profile when constructing the adapter.
    """
    if provider == "deepseek" or "deepseek.com" in base_url:
        return DEEPSEEK_PROFILE
    if provider == "openai" or "api.openai.com" in base_url:
        return OPENAI_PROFILE
    return DEFAULT_PROFILE
```

---

## Phase 3 — ModelClient protocol

**File: `src/haxjobs/model/protocol.py`** (NEW)

```python
from typing import Protocol, runtime_checkable
from collections.abc import AsyncIterator
from .types import ModelResponse, ModelStreamEvent, ModelMessage, ToolDefinition

class ModelRequest:
    """Immutable request for one model call."""
    messages: list[ModelMessage]
    tools: list[ToolDefinition] | None
    system: str | None
    max_tokens: int
    temperature: float

@runtime_checkable
class ModelClient(Protocol):
    """What agent_core sees — a sealed provider boundary.
    
    Implementations: GenericAdapter (real), FakeModelClient (tests).
    """
    async def complete(self, request: ModelRequest) -> ModelResponse: ...
    async def stream(self, request: ModelRequest) -> AsyncIterator[ModelStreamEvent]: ...
```

---

## Phase 4 — StreamAccumulator

**File: `src/haxjobs/model/streaming.py`** (NEW)

Pure sync. Takes stream deltas, accumulates state, emits typed events. Zero async. Testable with plain strings.

```python
@dataclass
class StreamAccumulator:
    profile: ProviderProfile

    # Internal state
    _accumulated_text: str = ""
    _accumulated_reasoning: str = ""
    _tool_calls: dict[int, dict] = field(default_factory=dict)
    _finish_reason: str | None = None
    _input_tokens: int = 0
    _output_tokens: int = 0

    def feed_text(self, text: str) -> ModelStreamEvent:
        """Feed text delta. Returns TEXT_DELTA event."""

    def feed_reasoning(self, text: str) -> ModelStreamEvent | None:
        """Feed reasoning delta. Returns THINKING_DELTA event or None if profile doesn't support it."""

    def feed_tool_call(self, index: int, call_id: str, name: str, args: str) -> ModelStreamEvent | None:
        """Feed tool call delta. Returns TOOL_CALL_DELTA or TOOL_CALL_DONE."""

    def feed_finish(self, reason: str, input_tokens: int, output_tokens: int) -> None:
        """Feed finish reason + usage."""

    def build(self) -> tuple[str, str | None, list[dict] | None, dict[str, int]]:
        """Return (text, reasoning_content, tool_calls, usage)."""
```

This replaces the inline stream-handler state machine currently buried inside `client.py:stream()`.

---

## Phase 5 — GenericAdapter

**File: `src/haxjobs/model/adapter.py`** (NEW)

One class implementing `ModelClient`. Reads `ProviderProfile` flags. Never branches on provider name.

```python
class GenericAdapter:
    def __init__(self, config: ProviderConfig, profile: ProviderProfile):
        self._config = config
        self._profile = profile
        self._client = openai.AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
        )

    async def complete(self, request: ModelRequest) -> ModelResponse:
        # Build params: model, messages, tools, {profile.max_tokens_field}, temperature
        # Add profile.extra_body
        # Add profile.reasoning_effort_field if set
        # Call self._client.chat.completions.create(params)
        # Read msg.content, msg.reasoning_content
        # If profile.requires_reasoning_preservation and msg.reasoning_content:
        #     response.reasoning_content = msg.reasoning_content
        # Return ModelResponse(...)

    async def stream(self, request: ModelRequest) -> AsyncIterator[ModelStreamEvent]:
        # Build params (same as complete but stream=True + stream_options)
        # accumulator = StreamAccumulator(self._profile)
        # For each chunk:
        #     if chunk.delta.content: yield accumulator.feed_text(...)
        #     if profile.thinking_format == "deepseek" and chunk.delta.reasoning_content:
        #         yield accumulator.feed_reasoning(...)
        #     if chunk.delta.tool_calls: yield accumulator.feed_tool_call(...)
        #     if chunk.choices[0].finish_reason: accumulator.feed_finish(...)
        # After loop: yield DONE event with accumulator.build()
```

Key design decisions:
- `thinking_format == "deepseek"` is the ONLY place the word "deepseek" appears in the adapter.
- Every other decision reads a profile flag.
- Adding Anthropic means adding a constant with `thinking_format="anthropic"`. The adapter already handles `"disabled"` (skip reasoning) and `"deepseek"` (capture `reasoning_content`). Adding `"anthropic"` (capture `thinking` content block) would be a flag-driven branch, not a provider branch.

---

## Phase 6 — ProviderConfig extraction

**File: `src/haxjobs/model/provider.py`** (NEW)

Extract config loading from `client.py`. Already partially done in `model/client.py:OpenAIModelClient.__init__`.

```python
@dataclass
class ProviderConfig:
    provider: str       # "deepseek"
    model: str          # "deepseek-v4-flash"
    base_url: str       # "https://api.deepseek.com/v1"
    api_key: str        # from haxjobs.toml

class ProviderConfigError(Exception): ...

def load_provider_config(path: Path | None = None) -> ProviderConfig:
    """Load provider config from haxjobs.toml. Raises ProviderConfigError."""
```

---

## Phase 7 — Tool schema conversion

**File: `src/haxjobs/model/schemas.py`** (NEW)

Extract tool definition → OpenAI JSON schema conversion. Currently in `client.py` and `turn.py` as inline dict builders.

```python
def tool_to_openai_schema(tool: ToolDefinition) -> dict:
    """Convert a HaxJobs ToolDefinition to OpenAI JSON schema dict."""

def tools_to_openai_schemas(tools: list[ToolDefinition]) -> list[dict]:
    """Convert all tools."""
```

---

## Phase 8 — Wire the agent loop

**File: `src/haxjobs/agent_core/turn.py`**

1. Import `ModelClient` (protocol), `ProviderProfile`, `detect_profile`, `ProviderConfig`
2. Accept `model_client: ModelClient` and `profile: ProviderProfile` instead of the old monolithic client
3. Add `THINKING_DELTA` branch in the stream handler:
   ```python
   elif stream_event.event_type == ModelStreamEventType.THINKING_DELTA:
       accumulated_reasoning += stream_event.delta
       # Not forwarded to LiveEvent (thinking is internal)
   ```
4. When persisting `AssistantMessage` after tool calls: include `reasoning_content=accumulated_reasoning`
5. When building the in-loop `ModelMessage` for the next request: include `reasoning_content=accumulated_reasoning or None`
6. Reset `accumulated_reasoning` each loop iteration alongside `accumulated_text`

**File: `src/haxjobs/agent_core/messages.py`**

1. `MessageProjector` gains `_pending_reasoning_content: str = ""`
2. `project()` when processing `assistant` messages: set `self._pending_reasoning_content = getattr(msg, "reasoning_content", "")`
3. `_flush()`: set `reasoning_content` on the `ModelMessage` if pending content exists
4. `MessageProjector.reset()`: clear `_pending_reasoning_content`

---

## Phase 9 — Wire composition root and delete old code

**File: `src/haxjobs/employment/composition.py`**

Replace the direct `OpenAIModelClient()` construction with:
```python
config = load_provider_config()
profile = detect_profile(config.provider, config.base_url)
model_client = GenericAdapter(config, profile)
```

**File: `src/haxjobs/model/client.py`** — DELETED

The 300-line monolith is replaced by protocol + adapter + profiles + schemas + streaming + provider.

**File: `src/haxjobs/model/__init__.py`** — updated exports

Export `ModelClient`, `GenericAdapter`, `ProviderProfile`, `ProviderConfig`, `detect_profile`, tool schema helpers.

---

## Files summary

| File | Action |
|---|---|
| `model/types.py` | Add `THINKING_DELTA`, `reasoning_content` on `ModelMessage` + `ModelResponse` |
| `model/protocol.py` | NEW — `ModelClient` protocol + `ModelRequest` |
| `model/profiles.py` | NEW — `ProviderProfile` + `detect_profile()` + 3 constants |
| `model/adapter.py` | NEW — `GenericAdapter` implementing `ModelClient` |
| `model/provider.py` | NEW — `ProviderConfig` + `load_provider_config()` |
| `model/schemas.py` | NEW — `tool_to_openai_schema()` helpers |
| `model/streaming.py` | NEW — `StreamAccumulator` |
| `model/client.py` | DELETED |
| `model/__init__.py` | Updated exports |
| `model/fake.py` | Unchanged |
| `agent_core/turn.py` | `THINKING_DELTA` branch, accumulate + persist + in-loop reasoning |
| `agent_core/messages.py` | `reasoning_content` on `AssistantMessage`, `_pending_reasoning_content` in projector |
| `agent_core/live_events.py` | Unchanged (THINKING_DELTA intentionally not forwarded) |
| `employment/composition.py` | Wire config → profile → adapter |
| `tests/` | New tests + update existing adapter callers |

---

## Tests

### New test files

1. **`tests/test_stream_accumulator.py`** — unit tests for `StreamAccumulator` with all three formats (`"disabled"`, `"deepseek"`, `"disabled"` again for edge cases)
2. **`tests/test_adapter.py`** — mock OpenAI SDK, test complete/stream with DeepSeek profile, test complete/stream with default profile, test that `thinking_format="disabled"` never produces THINKING_DELTA events
3. **`tests/test_profiles.py`** — `detect_profile()` returns correct profile for deepseek/openai/unknown

### New tests in existing files

4. **`tests/test_conversation_messages.py`** — `AssistantMessage` with `reasoning_content` round-trips through JSON; old JSON without the field parses fine
5. **`tests/test_turn_runtime.py`** — fake-stream test with tool calls asserting `fake.requests[1]` contains `reasoning_content` on the assistant message with tool calls (critical: in-loop ModelMessage path)
6. **`tests/test_model_streaming.py`** — mocked DeepSeek stream yielding reasoning deltas before text deltas, accumulated reasoning preserved on final message

### Required assertions

- `THINKING_DELTA` events are never forwarded to `LiveEvent`
- `thinking_format="disabled"` (default profile) ignores `reasoning_content` chunks entirely
- `requires_reasoning_preservation=True` attaches reasoning to BOTH the canonical `AssistantMessage` and the in-loop `ModelMessage`
- Session resume: `MessageProjector` carries reasoning_content from persisted `AssistantMessage` to provider-bound `ModelMessage`
- `model_dump(exclude_none=True)` omits `reasoning_content` when `None`
- All existing 290+ tests pass unchanged

---

## Verification

```bash
PYTHONPATH=src:. uv run python3 -m pytest -q tests/
PYTHONPATH=src:. uv run python3 -m py_compile $(find src -name '*.py')
uv lock --check
git diff --check
```

## Live validation

```bash
haxjobs chat --new
# Multi-turn conversation with tool calls
# Verify: sentences complete, no fragments
# Verify: no 400 errors on subsequent turns
# Verify: chat feels natural (reasoning = better quality)
```

---

## Out of scope

- Adding new provider profiles beyond DeepSeek (OpenAI and DEFAULT are included as constants, not wired)
- Context cache hit tracking (`prompt_cache_hit_tokens`)
- `user_id` session isolation for DeepSeek
- Anthropic messages API adapter (a separate adapter for non-OpenAI-compatible APIs, needed only when Claude Opus is directly supported)
- TUI thinking indicator
- `reasoning_effort` parameter control (default is fine for v1)
- Provider fallback cascade
- Async HTTP client (keep `asyncio.to_thread` wrapping for now)

---

> **Warning for executor:** This plan replaces the entire `model/client.py`. Before deleting it, verify ALL callers. The only callers should be `employment/composition.py` (construction), `agent_core/turn.py` (protocol usage), and tests (fake client). If `model/client.py` is imported from any other file, update that caller first. Do not create compatibility wrappers — delete `client.py` cleanly. When building the adapter, study Pi's `openai-completions.js` `getCompat()` + `detectCompat()` pattern at `/home/hax/.pi/agent/npm/node_modules/@earendil-works/pi-ai/dist/providers/openai-completions.js` lines 861-942 for the flag-driven approach and lines 93-130 for the thinking/text/tool-call event dispatch loop.
