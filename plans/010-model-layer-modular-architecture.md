# Plan 010 — Provider abstraction layer

> **Baseline:** `8f10995` (current main)
> **Drift stamp:** 2026-07-26
> **Status:** TODO
> **Depends on:** Plan 009 DONE

## Goal

Replace the single-provider `OpenAIModelClient` with a declarative provider layer. Each provider describes its quirks as flags (`thinkingFormat`, `requiresReasoningContentOnToolTurns`, etc.) and a single `UnifiedAdapter` reads those flags to adjust behavior. Adding a new provider means adding a config entry, not writing a new adapter class.

This also fixes the DeepSeek streaming bug as a side effect — `reasoning_content` capture and preservation is a compat flag, not hardcoded.

Pattern stolen from Pi v0.80.6's `model-registry.js` and `provider-attribution`, which uses `OpenAICompletionsCompatSchema` with 12+ declarative flags instead of per-provider adapter classes.

---

## Architecture — what good looks like

```
model/
├── __init__.py         # exports
├── types.py            # ModelMessage, ModelRequest, ModelResponse, ModelStreamEvent
│                        #   + THINKING_DELTA event type
│                        #   + reasoning_content on ModelResponse and ModelMessage
├── protocol.py          # ModelClient protocol (moved from client.py)
├── compat.py            # ProviderCompat — declarative capability flags
├── adapter.py           # UnifiedAdapter — one adapter, reads compat to adjust
├── provider.py          # ProviderConfig — loads from haxjobs.toml, includes compat
├── fake.py              # unchanged
└── schemas.py           # tool schema conversion helpers (moved from client.py)

agent_core/
├── messages.py          # + reasoning_content on AssistantMessage
│                        #   + _pending_reasoning_content in MessageProjector
└── turn.py              # accumulate reasoning in loop, preserve on in-loop message
```

### Import rules (enforced)

1. `model/` imports nothing above it — only `config` and stdlib
2. `agent_core/` imports only `model/` and stdlib — never `employment/`, never `interfaces/`

---

## Core design — `ProviderCompat`

```python
class ProviderCompat(BaseModel):
    """Declarative flags describing how a provider diverges from standard OpenAI."""

    # Thinking mode
    thinking_format: Literal["disabled", "openai", "deepseek"] = "disabled"
    reasoning_effort_supported: bool = False

    # DeepSeek requires reasoning_content on assistant messages that made tool calls
    requires_reasoning_content_on_tool_turns: bool = False

    # Field name for max output tokens (OpenAI uses max_completion_tokens)
    max_tokens_field: Literal["max_tokens", "max_completion_tokens"] = "max_tokens"

    # Whether stream_options works
    supports_usage_in_streaming: bool = True

    # Extra body params added to every request at the top level
    extra_body: dict = Field(default_factory=dict)
```

DeepSeek entry:
```python
ProviderCompat(
    thinking_format="deepseek",
    reasoning_effort_supported=True,
    requires_reasoning_content_on_tool_turns=True,
    extra_body={"thinking": {"type": "enabled"}},
)
```

OpenAI entry (future):
```python
ProviderCompat(
    thinking_format="disabled",
    max_tokens_field="max_completion_tokens",
    supports_usage_in_streaming=True,
)
```

Anthropic entry (future):
```python
ProviderCompat(
    thinking_format="disabled",
    max_tokens_field="max_tokens",
    supports_usage_in_streaming=False,
)
```

---

## Core design — `ProviderConfig`

```python
class ProviderConfig(BaseModel):
    """Per-provider config loaded from ~/.haxjobs/haxjobs.toml."""

    name: str                               # "deepseek"
    model: str                              # "deepseek-v4-pro"
    api_key: str
    base_url: str                           # "https://api.deepseek.com/v1"
    compat: ProviderCompat = Field(default_factory=ProviderCompat)

    @classmethod
    def from_file(cls, path: Path) -> ProviderConfig: ...
```

The existing `haxjobs.toml` format stays the same:
```toml
[provider]
name = "deepseek"
model = "deepseek-v4-pro"
api_key = "sk-..."
base_url = "https://api.deepseek.com/v1"
```

The `compat` is derived from the provider `name` internally, not stored in the TOML. A lookup table maps provider name → compat flags. Adding a new provider means adding one entry to that table plus a config entry in the TOML.

---

## Core design — `UnifiedAdapter`

```python
class UnifiedAdapter:
    """Single adapter that reads ProviderCompat to adjust behavior.

    Replaces OpenAIModelClient. No per-provider subclasses.
    """

    def __init__(self, config: ProviderConfig):
        self._config = config
        self._compat = config.compat
        self._client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            max_retries=0,
        )

    def _build_request(self, request: ModelRequest, stream: bool) -> dict:
        """Build the API call dict, respecting compat flags."""
        body = {
            "model": self._config.model,
            "messages": [...],
            self._compat.max_tokens_field: request.max_tokens,
        }
        if stream and self._compat.supports_usage_in_streaming:
            body["stream_options"] = {"include_usage": True}
        if self._compat.extra_body:
            body["extra_body"] = self._compat.extra_body
        if self._compat.reasoning_effort_supported:
            body["reasoning_effort"] = "high"
        if request.tools:
            body["tools"] = tool_schemas_to_provider(request.tools)
        return body

    # complete() and stream() — same as current OpenAIModelClient
    # but stream() routes reasoning_content when thinking_format != "disabled"
```

---

## Reasoning_content data flow (end to end)

```
1. DeepSeek sends:          delta.reasoning_content ("Let me think...")
                            delta.content ("The answer is...")

2. adapter.stream():        if compat.thinking_format == "deepseek":
                                yield THINKING_DELTA(delta.reasoning_content)
                            yield TEXT_DELTA(delta.content)

3. turn.py loop:            accumulated_reasoning += stream_event.delta  (THINKING_DELTA)
                            accumulated_text += stream_event.delta      (TEXT_DELTA)

4. After tool calls:        New AssistantMessage(
                                content=accumulated_text,
                                reasoning_content=accumulated_reasoning,  ← persists
                            )

5. In-loop provider msg:    ModelMessage(
                                role="assistant",
                                tool_calls=[...],
                                reasoning_content=accumulated_reasoning or None,  ← immediate
                            )

6. On session resume:       MessageProjector reads AssistantMessage.reasoning_content
                            → _pending_reasoning_content
                            → _flush() sets it on projected ModelMessage

7. model_dump(exclude_none=True): only sends reasoning_content when not None
```

---

## Files in scope

| File | Change |
|---|---|
| `model/types.py` | Add THINKING_DELTA, reasoning_content on ModelResponse + ModelMessage |
| `model/compat.py` | NEW — ProviderCompat model, provider name → compat lookup table |
| `model/provider.py` | NEW — ProviderConfig, from_file() classmethod |
| `model/protocol.py` | NEW — ModelClient protocol (moved from client.py) |
| `model/schemas.py` | NEW — tool_schemas_to_provider(), provider_to_internal_tool_call() |
| `model/adapter.py` | NEW — UnifiedAdapter implementing ModelClient |
| `model/__init__.py` | Updated exports |
| `model/client.py` | DELETED — superseded by protocol + adapter + provider |
| `agent_core/messages.py` | reasoning_content on AssistantMessage, _pending_reasoning_content in projector |
| `agent_core/turn.py` | THINKING_DELTA handler, accumulated_reasoning, set on both messages |
| `employment/composition.py` | Import UnifiedAdapter instead of OpenAIModelClient |
| `tests/` | New tests for compat, adapter, reasoning preservation |

## Files NOT touched

- `agent_core/session.py` — no session logic changes
- `agent_core/live_events.py` — no new LiveEventType (thinking is NOT forwarded)
- `agent_core/tools.py` — no tool contract changes
- `model/fake.py` — unchanged
- `interfaces/*` — TUI only renders LiveEvents, THINKING_DELTA is intentionally silent
- `employment/*` except composition.py

---

## Implementation phases

### Phase 1 — New model modules (no behavior change yet)

1. Create `model/compat.py` — ProviderCompat model, provider lookup table
2. Create `model/provider.py` — ProviderConfig, from_file()
3. Create `model/protocol.py` — ModelClient protocol (copy from client.py)
4. Create `model/schemas.py` — helper functions (extract from client.py)
5. Update `model/__init__.py` exports
6. Tests: compat flags lookup, provider config loading, schema round-trip

### Phase 2 — UnifiedAdapter

1. Create `model/adapter.py` — UnifiedAdapter with `_build_request()` respecting compat flags
2. adapter.stream() handles thinking_format for reasoning_content capture
3. adapter.complete() captures reasoning_content in ModelResponse
4. Tests: DeepSeek compat sends extra_body, OpenAI compat does not, reasoning capture

### Phase 3 — Turn loop and projector

1. Add reasoning_content to ModelMessage, ModelResponse, ModelStreamEventType in types.py
2. Add reasoning_content to AssistantMessage in messages.py
3. MessageProjector carries _pending_reasoning_content
4. turn.py accumulates reasoning, sets on both canonical and in-loop messages
5. Tests: in-loop message has reasoning, projector preserves it, backward compat

### Phase 4 — Wiring and cleanup

1. composition.py imports UnifiedAdapter instead of OpenAIModelClient
2. Delete model/client.py
3. Update all imports across codebase
4. Full test suite pass

## Tests (must pass)

1. `deepseek_compat = CompatRegistry.get("deepseek")` has thinking_format="deepseek" and requires_reasoning_content_on_tool_turns=True
2. Adapter build_request() includes extra_body for DeepSeek, not for a provider with no extra_body
3. Adapter stream yields THINKING_DELTA before TEXT_DELTA for DeepSeek
4. In-loop provider message carries reasoning_content after tool calls (fake-stream test asserting `fake.requests[1]`)
5. AssistantMessage with reasoning_content round-trips through canonical JSON
6. Session resume: projector reads reasoning_content from persisted AssistantMessage
7. Thinking content never appears in LiveEvent
8. Existing test suite — all 290 tests pass

## Verification

```bash
PYTHONPATH=src:. uv run -- python3 -m pytest -q tests/
PYTHONPATH=src:. uv run -- python3 -m py_compile $(find src -name '*.py')
uv lock --check
git diff --check
```

Live: `haxjobs chat --new` with multi-turn tool calls, verify streaming is smooth, no 400 errors.

## Out of scope

- Provider fallback cascade
- Retry logic
- Anthropic API format adapter
- Context caching (prompt_cache_hit_tokens tracking)
- user_id session isolation
- Token usage tracking dashboard
- TUI thinking indicator
- Runtime provider switching mid-session
- Provider credentials migration

---

> **Warning for executor:** This plan adds 5 new files to model/ and deletes 1. Before implementing, check that the files listed for creation don't already exist and that model/client.py still has the exact shape described. The compat flags model should be treated as a stable API — adding a flag should never break existing providers. Every new flag must have a safe default.
