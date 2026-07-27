# Plan 010 — Provider abstraction layer

> **Baseline:** `8f10995` (current main)
> **Drift stamp:** 2026-07-26
> **Status:** ACCEPTED (codex-reviewed, round 3)
> **Depends on:** Plan 009 DONE

## Goal

Build a proper provider abstraction layer that supports multiple LLM providers (DeepSeek, OpenAI, Anthropic, Kimi, etc.) and isolates all provider-specific behavior behind compat flags. Currently only DeepSeek is connected, but adding a new provider should be one adapter class, not scattered if-statements in the agent loop.

This is also the fix for the broken DeepSeek streaming. The root cause is that `reasoning_content` chunks are silently dropped. The fix flows naturally from a proper adapter architecture.

## Architecture (inspired by Pi v0.80.6 and Hermes v0.16.0)

Both Pi and Hermes use the same fundamental pattern: **compat flags on the model definition, not provider-specific code in the agent loop.** The agent loop calls `model.stream(request)` and handles `ModelStreamEvent` objects. It never knows which provider is behind the call. The adapter owns every provider-specific detail.

```
model/                                  provider boundary
├── __init__.py                         re-exports
├── types.py                            ModelMessage, ModelRequest, ModelResponse,
│                                       ModelStreamEvent, ModelFailure — unchanged API
├── protocol.py                         ModelClient protocol (extracted from client.py)
├── provider_config.py                  ModelConfig — loaded from haxjobs.toml
│                                       compat flags per model, not per provider
├── adapters/
│   ├── __init__.py
│   ├── base.py                         BaseAdapter — shared logic
│   └── openai_compat.py                OpenAICompatAdapter — any OpenAI-compatible endpoint
├── fake.py                             FakeModelClient — unchanged
└── (client.py deleted)

agent_core/                             unchanged except reasoning_content in messages.py + turn.py
employment/composition.py               wires ModelConfig → adapter → session
```

### How compat flags work (the Pi pattern)

Each model config carries a flat set of boolean/string flags:

```python
@dataclass
class ModelConfig:
    provider: str              # "deepseek", "openai", "anthropic"
    model_id: str              # "deepseek-v4-pro", "gpt-5.6"
    api_type: str              # "openai_completions" or "anthropic_messages"
    base_url: str
    api_key: str

    # Capability flags — the adapter reads these, the agent loop does not
    supports_thinking: bool = False
    supports_reasoning_content: bool = False
    requires_reasoning_on_tool_turns: bool = False
    supports_streaming: bool = True
    supports_tool_calls: bool = True
    supports_json_mode: bool = False

    # Provider-specific request body additions
    extra_body: dict | None = None

    # Limits
    context_window: int = 128_000
    max_output_tokens: int = 32_768

    @classmethod
    def from_file(cls, path: Path) -> "ModelConfig": ...
```

When `extra_body` is `{"thinking": {"type": "enabled"}}` for DeepSeek, the adapter injects it. When `requires_reasoning_on_tool_turns` is True, the projection layer preserves reasoning_content. The adapter reads flags. The agent loop reads `ModelStreamEvent`. They meet only through the protocol.

### Why this matters (adding a new provider)

Adding Anthropic later:

1. Add `anthropic_messages` adapter class in `adapters/anthropic.py` (~150 lines)
2. Add `ModelConfig(provider="anthropic", model_id="claude-opus-4-8", api_type="anthropic_messages", ...)` 
3. Agent loop, tool dispatch, session store, terminal — **zero changes.**

Without this architecture, adding Anthropic means: check `self._provider == "deepseek"` in the stream handler, check it again in response parsing, check it in tool schema conversion, check it in error handling. The if-statements spread everywhere. That's the current trajectory.

---

## Phases

### Phase 1 — ModelConfig from haxjobs.toml

**New file: `model/provider_config.py`**

`ModelConfig` dataclass with the fields above plus `from_file(path)` classmethod that reads `~/.haxjobs/haxjobs.toml` and builds a config:

```toml
[provider]
name = "deepseek"
model = "deepseek-v4-pro"
api_key = "..."
base_url = "https://api.deepseek.com/v1"
```

Defaults are sensible for DeepSeek. The `api_type` defaults to `"openai_completions"`. `extra_body` is `{"thinking": {"type": "enabled"}}` when provider is `"deepseek"`. Other providers get empty `extra_body`.

**Tests:** Load from valid TOML, missing file, missing required keys, defaults, DeepSeek gets thinking extra_body, non-DeepSeek does not.

---

### Phase 2 — ModelClient protocol extraction

**New file: `model/protocol.py`**

```python
class ModelClient(Protocol):
    async def complete(self, request: ModelRequest) -> ModelResponse | ModelFailure: ...
    def stream(self, request: ModelRequest, cancel_event: asyncio.Event) -> AsyncIterator[ModelStreamEvent]: ...
```

Extracted from `model/client.py`. No new logic.

**Changed:** `model/client.py` imports from protocol instead of defining it inline. `model/__init__.py` export path changes.

---

### Phase 3 — OpenAICompatAdapter (replaces OpenAIModelClient)

**New file: `model/adapters/base.py`** — `BaseAdapter` with shared `_tool_schemas_to_provider()` and `_model_dump_messages()`.

**New file: `model/adapters/openai_compat.py`** — `OpenAICompatAdapter(BaseAdapter)`:

- Constructor takes `ModelConfig`, creates `AsyncOpenAI(config.base_url, config.api_key)`
- `_build_request(request)` returns the full kwargs dict including:
  - Standard: `model`, `messages`, `max_tokens`, `tools`
  - Config-driven: `extra_body` from `config.extra_body`
  - Streaming: `stream=True`, `stream_options={"include_usage": True}`
- `complete(request)` — non-stream call, returns `ModelResponse` with `reasoning_content`
- `stream(request, cancel_event)` — opens stream, yields `ModelStreamEvent` objects:
  - `delta.content` → `TEXT_DELTA`
  - `delta.reasoning_content` → `THINKING_DELTA` (when `config.supports_reasoning_content`)
  - Accumulated tool calls → `COMPLETE_TOOL_CALL`
  - Stream end → `RESPONSE_COMPLETED` or `RESPONSE_FAILED`

Key design: the adapter checks `config.supports_reasoning_content` before handling `delta.reasoning_content`. The agent loop handles `THINKING_DELTA` events unconditionally. If a provider doesn't support reasoning, the event is never emitted.

**Changed file:** `model/__init__.py` — export `OpenAICompatAdapter` instead of `OpenAIModelClient`
**Deleted:** Nothing yet. Old `client.py` still exists.

**Tests:** 
- Adapter builds correct API call with thinking extra_body
- Stream yields THINKING_DELTA for reasoning_content chunks (when supported)
- Stream correctly accumulates tool calls across multiple delta chunks  
- Cancellation handled (cancel event → RESPONSE_FAILED)
- Non-stream complete() populates reasoning_content field
- Non-DeepSeek config omits thinking extra_body

---

### Phase 4 — Model types update (reasoning_content)

**File: `model/types.py`**

- Add `THINKING_DELTA` to `ModelStreamEventType` enum
- Add `reasoning_content: str = ""` to `ModelResponse`
- Add `reasoning_content: str | None = None` to `ModelMessage`

**File: `agent_core/messages.py`**

- Add `reasoning_content: str = ""` to `AssistantMessage` (remove `extra: forbid` constraint or add as explicit field)

**Tests:** THINKING_DELTA serialization, AssistantMessage round-trip with new field, backward compat (old JSON without field parses).

---

### Phase 5 — Reasoning accumulation in turn loop + projector

**File: `agent_core/turn.py`**

In the main loop, reset `accumulated_reasoning = ""` alongside `accumulated_text = ""`.

In the stream event handler, add:

```python
elif stream_event.event_type == ModelStreamEventType.THINKING_DELTA:
    accumulated_reasoning += stream_event.delta
    # Not emitted as LiveEvent — reasoning is internal to the model
```

When persisting `AssistantMessage` after a tool call turn, include `reasoning_content=accumulated_reasoning`.

**Critical:** when building the in-loop `ModelMessage` for the immediate next request (the one that bypasses the projector at turn.py ~line 551), include `reasoning_content=accumulated_reasoning or None`.

**File: `agent_core/messages.py`**

Add `_pending_reasoning_content: str = ""` to `MessageProjector.__init__`. Clear it in `project()` reset. Set it when processing `assistant` kind: `self._pending_reasoning_content = getattr(msg, "reasoning_content", "")`. In `_flush()`, set `msg.reasoning_content = self._pending_reasoning_content` when non-empty.

**Tests:** 
- Fake stream with tool call verifies next request has reasoning_content
- Multi-turn conversation preserves reasoning across tool-call boundaries in projector
- Thinking not leaked as LiveEvent

---

### Phase 6 — Wiring and cleanup

**File: `employment/composition.py`**

Change `from haxjobs.model.client import ModelClient, OpenAIModelClient` to `from haxjobs.model.protocol import ModelClient` and `from haxjobs.model.adapters.openai_compat import OpenAICompatAdapter`. Create adapter from config:

```python
config = ModelConfig.from_file(PROVIDER_CONFIG_PATH)
model = OpenAICompatAdapter(config)
```

**File: `model/__init__.py`** — remove `OpenAIModelClient`, add `OpenAICompatAdapter`, `ModelConfig`, `ModelClient`

**Deleted: `model/client.py`**

**All existing tests must pass.** All imports in tests that reference `OpenAIModelClient` must change.

---

## Files in scope

| File | Change |
|---|---|
| `model/provider_config.py` | New — ModelConfig dataclass |
| `model/protocol.py` | New — ModelClient protocol (extracted) |
| `model/adapters/base.py` | New — shared adapter logic |
| `model/adapters/openai_compat.py` | New — replaces OpenAIModelClient |
| `model/types.py` | THINKING_DELTA, reasoning_content fields |
| `model/client.py` | Deleted |
| `model/__init__.py` | Updated exports |
| `agent_core/turn.py` | Accumulate reasoning, reasoning on in-loop ModelMessage |
| `agent_core/messages.py` | reasoning_content on AssistantMessage, projector carries it |
| `employment/composition.py` | Wire ModelConfig → adapter |
| `tests/` | New tests for ModelConfig, adapter, stream flow, reasoning preservation |

## Out of scope

- StreamAccumulator class (accumulation stays in adapter, simple enough for now)
- Anthropic API format adapter (API type `"anthropic_messages"` is declared but not implemented)
- Provider selection / multiple configured providers
- Provider fallback / retry
- Token usage tracking improvements
- Context cache tracking (DeepSeek `prompt_cache_hit_tokens`)
- TUI thinking indicator
- Tool dispatch extraction from turn.py
- `reasoning_effort` control (default "high" is fine)

## Verification

```bash
PYTHONPATH=src:. uv run -- python3 -m pytest -q tests/
PYTHONPATH=src:. uv run -- python3 -m py_compile $(find src tests -name '*.py')
uv lock --check
git diff --check
```

**Live validation:** `haxjobs chat --new` with a message requiring tool calls. Verify sentences arrive complete, no 400 errors on multi-turn.

## STOP conditions

- Any test regression in the 290-test suite
- Import cycle between model/ and agent_core/ or employment/
- Provider-specific logic leaks into agent_core (no `if self._provider == "deepseek"` outside model/adapters/)

---

> **Warning for executor:** This plan describes the target architecture. Before implementing, compare every claim against the live code at the current HEAD. The adapter replaces `OpenAIModelClient` — all callers must be updated. The `ModelClient` protocol shape must remain identical so `FakeModelClient` and all tests continue to work.
