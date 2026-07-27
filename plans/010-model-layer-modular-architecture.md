# Plan 010 — Provider Abstraction Layer

> **Baseline:** `8f10995` (current main)
> **Drift stamp:** 2026-07-26
> **Status:** ACCEPTED (codex-reviewed round 3)
> **Depends on:** Plan 009 DONE

## Goal

Replace the monolithic `model/client.py` with a proper provider abstraction layer that supports multiple providers through composable compat flags, not one-off if/else chains. Fix the DeepSeek streaming bug as a side effect of getting the abstraction right, not as the primary goal.

The pattern is borrowed from Pi's model registry: a single generic adapter that reads provider profiles containing boolean compat flags, a thinking format enum, and request-template kwargs. Adding a new provider means adding one ~30-line profile dataclass. Zero adapter changes.

---

## Current state — what's broken

### Architecture problem

`model/client.py` (300 lines) is a single class doing everything:

```text
OpenAIModelClient
├── _ensure_client()        # loads TOML, builds AsyncOpenAI — mixed with provider config
├── complete()              # non-stream path
│   ├── model_dump() + tools loop  # tool schema conversion inline
│   └── bare str(exc)              # leaks provider internals into safe failures
└── stream()                # stream path
    ├── tool schema conversion (DUPLICATED from complete)
    ├── delta.content only          # drops reasoning_content silently
    ├── tool call accumulation      # untestable inside async generator
    └── RESPONSE_FAILED on cancel   # correct but tangled with IO
```

Adding Anthropic support with this design would require if/else branches inside stream(), complete(), and _ensure_client() — a fast track to a 600-line unmaintainable file.

### Streaming bug root cause

1. `model/client.py:213` — only handles `delta.content`. DeepSeek sends `delta.reasoning_content` chunks first, then `delta.content`. Reasoning is silently dropped.
2. `model/types.py:77-82` — `ModelStreamEventType` has no `THINKING_DELTA`. Reasoning has nowhere to go.
3. `model/types.py:26-31` — `ModelMessage` has no `reasoning_content` field.
4. `agent_core/messages.py:34-45` — `AssistantMessage` has no `reasoning_content` field and `extra: forbid`.
5. `agent_core/messages.py:93-107` — `MessageProjector._flush()` doesn't carry reasoning_content.
6. `agent_core/turn.py:551` — the in-loop `ModelMessage(role="assistant", tool_calls=...)` bypasses the projector entirely for the immediate next request.
7. DeepSeek requires `reasoning_content` on multi-turn tool-call messages or returns 400.

All seven must be fixed.

---

## Architecture — what good looks like

```
model/
├── __init__.py              # re-exports
├── types.py                 # ModelMessage (+reasoning_content), ModelStreamEvent (+THINKING_DELTA)
├── errors.py                # ModelFailure (unchanged)
├── protocol.py              # ModelClient protocol (extracted from client.py)
├── schemas.py               # tool schema conversion (extracted inline loops)
│
├── profiles/                # one file per provider — zero adapter changes to add a new one
│   ├── __init__.py          # registry: register(), get(), list()
│   ├── base.py              # ProviderProfile dataclass
│   └── deepseek.py          # DeepSeekProfile (~30 lines)
│
├── adapter.py               # GenericAdapter — reads profile, builds requests, streams
│                            #    the only file that talks to any provider SDK
├── provider.py              # ProviderConfig — loads from ~/.haxjobs/haxjobs.toml
└── fake.py                  # FakeModelClient (unchanged)

agent_core/
├── turn.py                  # agent loop — shrinks, accumulates reasoning_content
├── messages.py              # AssistantMessage (+reasoning_content), MessageProjector (+_pending_reasoning_content)
└── ...
```

### The key abstraction: ProviderProfile

```python
@dataclass
class ProviderProfile:
    """Provider-specific behaviors encoded as composable flags.

    Inspired by Pi's model-registry compat schemas.
    No methods — pure data. The generic adapter reads these flags
    and builds requests accordingly.
    """

    provider_id: str                    # "deepseek", "openai", "anthropic"
    display_name: str                   # "DeepSeek"
    api_mode: str                       # "openai-completions" | "anthropic-messages"

    # Request building
    base_url: str                       # https://api.deepseek.com/v1
    default_model: str                  # deepseek-v4-pro

    # Thinking mode support
    thinking_format: str                # "deepseek" | "openai" | "anthropic" | "disabled"
    thinking_level_map: dict[str, str | None]  # internal → provider (e.g. {"high": "high", "off": None})
    default_thinking_level: str          # "high"
    supports_reasoning_effort: bool
    supports_reasoning_content: bool      # whether to accumulate reasoning_content

    # Schema quirks (boolean flags — all default False)
    requires_reasoning_on_tool_messages: bool   # DeepSeek: True
    requires_tool_result_name: bool
    requires_assistant_after_tool_result: bool
    max_tokens_field: str               # "max_tokens" | "max_completion_tokens"

    # Static dict merged into request body for this provider.
    # DeepSeek: {"thinking": {"type": "enabled"}} (always send).
    # OpenAI: None (no extra body by default).
    # $var interpolation is deferred until a provider needs conditional extra_body.
    extra_body_template: dict | None
    
    # thinking_format labels what the provider expects in the thinking payload.
    # Used for logging/display only. The adapter reads the boolean flags
    # (supports_reasoning_content, supports_reasoning_effort) and
    # extra_body_template to build the actual request.
```

### How the generic adapter uses profiles

```python
class GenericAdapter:
    """One adapter, many providers. Reads a ProviderProfile at request time."""

    def __init__(self, config: ProviderConfig, profile: ProviderProfile):
        self._config = config
        self._profile = profile
        self._client = AsyncOpenAI(api_key=config.api_key, base_url=profile.base_url)

    def _build_request(self, request: ModelRequest) -> dict:
        """Build the provider-specific request dict.

        Does NOT hardcode DeepSeek behavior. Reads flags from the profile:
        - max_tokens: uses profile.max_tokens_field
        - extra_body: interpolates profile.extra_body_template with thinking settings
        - tool schemas: calls schemas.tool_schemas_to_provider()
        """
        ...

    async def stream(self, request, cancel_event) -> AsyncIterator[ModelStreamEvent]:
        """Stream with profile-aware delta handling.

        When profile.supports_reasoning_content is True:
        - reads delta.reasoning_content → yields THINKING_DELTA events
        When not True: skips that branch silently.
        """
        ...

    async def complete(self, request) -> ModelResponse | ModelFailure:
        """Non-stream with profile-aware response parsing.

        When profile.supports_reasoning_content:
        - reads msg.reasoning_content → includes in ModelResponse
        """
        ...
```

Adding Anthropic later: one `profiles/anthropic.py` with `api_mode: "anthropic-messages"`. If Anthropic needs a different SDK call shape, the adapter checks `api_mode`. Zero profile changes for existing providers.

---

## Implementation phases

### Phase 1 — Canonical types (pre-requisite for everything)

**Files: `model/types.py`, `agent_core/messages.py`**

- Add `THINKING_DELTA` to `ModelStreamEventType`
- Add `reasoning_content: str = ""` to `ModelResponse`
- Add `reasoning_content: str | None` to `ModelMessage` (default None, `exclude_none` omits it)
- Add `reasoning_content: str = ""` to `AssistantMessage` (default empty, backward compatible)

**Tests:** Round-trip serialization, backward compat without field, THINKING_DELTA enum value.

---

### Phase 2 — Provider profile registry

**New files: `model/profiles/__init__.py`, `model/profiles/base.py`, `model/profiles/deepseek.py`**

`profiles/base.py`:
```python
@dataclass
class ProviderProfile:
    provider_id: str
    display_name: str
    api_mode: str                    # "openai-completions"
    base_url: str
    default_model: str
    thinking_format: str             # "deepseek" | "disabled"
    thinking_level_map: dict
    default_thinking_level: str
    supports_reasoning_effort: bool
    supports_reasoning_content: bool
    requires_reasoning_on_tool_messages: bool
    requires_tool_result_name: bool  # default False
    requires_assistant_after_tool_result: bool  # default False
    max_tokens_field: str            # "max_tokens"
    extra_body_template: dict | None  # None
```

`profiles/deepseek.py`:
```python
DEEPSEEK_PROFILE = ProviderProfile(
    provider_id="deepseek",
    display_name="DeepSeek",
    api_mode="openai-completions",
    base_url="https://api.deepseek.com/v1",
    default_model="deepseek-v4-pro",
    thinking_format="deepseek",
    thinking_level_map={"off": None, "low": "low", "medium": "medium", "high": "high", "max": "max"},
    default_thinking_level="high",
    supports_reasoning_effort=True,
    supports_reasoning_content=True,
    requires_reasoning_on_tool_messages=True,
    max_tokens_field="max_tokens",
    extra_body_template={"thinking": {"type": "enabled"}},
)
```

`profiles/__init__.py`: `register(profile)`, `get(provider_id)`, `list_all()` — simple dict-backed registry.

**Tests:** Profile dataclass round-trip, registry get/register, default values.

---

### Phase 3 — Provider config and tool schemas

**New files: `model/provider.py`, `model/schemas.py`**

`model/provider.py` — extract from `client.py:36-56`:
```python
@dataclass
class ProviderConfig:
    api_key: str
    provider_id: str     # "deepseek"
    model: str           # "deepseek-v4-pro"
    @classmethod
    def from_file(cls, path: Path) -> ProviderConfig: ...
```

`model/schemas.py` — extract inline tool loops from `client.py:75-85,140-152`:
```python
def tool_schemas_to_provider(tools: list[ToolSchema]) -> list[dict]: ...
def provider_tool_call_to_internal(raw) -> ToolCall: ...
```

**Tests:** Config loading from TOML, tool schema round-trip.

---

### Phase 4 — Generic adapter + protocol extraction

**New files: `model/adapter.py`, `model/protocol.py`**

Extracts the stream and complete logic from `client.py`, makes it profile-aware.
Also moves the `ModelClient` protocol from `client.py` to `protocol.py` (mechanical extraction, ~10 lines).

1. `_build_request(request)` — uses `profile.max_tokens_field`, calls `schemas.tool_schemas_to_provider()`, interpolates `profile.extra_body_template`
2. `stream(request, cancel_event)` — uses `StreamAccumulator` for tool calls, checks `profile.supports_reasoning_content` before reading reasoning deltas, yields `THINKING_DELTA` events
3. `complete(request)` — same profile-aware logic, non-stream

**Tests:**
- DeepSeek profile: stream yields THINKING_DELTA for reasoning_content
- OpenAI profile (no reasoning support): reasoning_content branch skipped
- Tool call accumulation works across multiple delta chunks
- Static extra_body_template merged correctly
- Cancellation: cancel event set → RESPONSE_FAILED with "cancelled"
- `test_model_streaming.py`: delete two old `OpenAIModelClient` mock tests (they test the deleted class internals). Replace with adapter-level equivalents testing `GenericAdapter.stream()` with `supports_reasoning_content` toggled.

---

### Phase 5 — Wire the agent loop

**File: `agent_core/turn.py`**

1. Initialize `accumulated_reasoning = ""` inside the loop alongside `accumulated_text` (line 198)
2. Add THINKING_DELTA branch: `accumulated_reasoning += stream_event.delta` (no LiveEvent)
3. On canonical persistence: `AssistantMessage(reasoning_content=accumulated_reasoning, ...)`
4. **On in-loop provider message** (line ~551): `ModelMessage(reasoning_content=accumulated_reasoning or None, ...)`
5. Reset `accumulated_reasoning` each loop iteration

**File: `agent_core/messages.py`**

1. `MessageProjector.__init__` — add `self._pending_reasoning_content: str = ""`
2. `_flush()` — if `self._pending_reasoning_content`, set `msg.reasoning_content = self._pending_reasoning_content`
3. `project()` — when processing `assistant` message: `self._pending_reasoning_content = getattr(msg, "reasoning_content", "")`
4. Reset in `project()` init: `self._pending_reasoning_content = ""`

**Tests:**
- Fake-stream test with tool call: `fake.requests[1]` has reasoning_content on assistant message
- Session resume: projector carries reasoning_content from persisted AssistantMessage
- In-loop provider message test (critical path that bypasses projector)
- Thinking not leaked to LiveEvent

---

### Phase 6 — Composition root and cleanup

**File: `employment/composition.py`**

- Import `GenericAdapter` and `ProviderProfile` instead of `OpenAIModelClient`
- Load `ProviderConfig.from_file(PROVIDER_CONFIG_PATH)`
- Look up profile via `profiles.get(config.provider_id)`
- Construct `GenericAdapter(config, profile)`

**File: `model/client.py`**

- **Delete.** Replaced by `protocol.py` + `adapter.py` + `profiles/` + `provider.py` + `schemas.py`.

**Update all imports:**
- `agent_core/turn.py` — imports `ModelClient` from `model.protocol`
- `agent_core/session.py` — same
- `model/fake.py` — same
- `tests/test_model_streaming.py` — imports adapter directly
- `model/__init__.py` — re-exports updated

**Tests:** All 290 existing tests pass. New tests: 10-15.

---

## Files in scope

| File | Change |
|---|---|
| `model/types.py` | THINKING_DELTA enum, reasoning_content on ModelResponse + ModelMessage |
| `model/protocol.py` | NEW — ModelClient protocol (extracted, no new logic) |
| `model/profiles/__init__.py` | NEW — profile registry |
| `model/profiles/base.py` | NEW — ProviderProfile dataclass |
| `model/profiles/deepseek.py` | NEW — DeepSeekProfile (first provider) |
| `model/adapter.py` | NEW — GenericAdapter (profile-aware stream+complete) |
| `model/provider.py` | NEW — ProviderConfig from TOML |
| `model/schemas.py` | NEW — tool schema conversion |
| `model/client.py` | DELETED |
| `model/__init__.py` | Updated exports |
| `agent_core/turn.py` | reasoning_content accumulation + in-loop preservation |
| `agent_core/messages.py` | reasoning_content on AssistantMessage + MessageProjector |
| `employment/composition.py` | Wire GenericAdapter instead of OpenAIModelClient |
| `agent_core/__init__.py` | Updated exports |
| `tests/` | 10-15 new tests |

## Files NOT touched

- `interfaces/*` — TUI only renders LiveEvent, THINKING_DELTA not forwarded
- `agent_core/session.py` — no session logic changes
- `agent_core/live_events.py` — no new LiveEventType
- `agent_core/tools.py` — no tool contract changes
- `model/fake.py` — unchanged (imports ModelClient from protocol)
- `config.py` — PROVIDER_CONFIG_PATH unchanged

## Out of scope

- Anthropic API mode adapter (the GenericAdapter currently only does openai-completions mode; add Anthropic when you add your first Anthropic-keyed provider)
- OpenAI/gpt-5.6 profile (trivial: one ~30-line profile dataclass after this lands)
- Claude Opus profile (same — one profile dataclass)
- User-facing "/model" command or model switching UX
- Context cache hit tracking (`prompt_cache_hit_tokens`)
- Token cost tracking per request
- Retry logic / fallback cascade
- Tool dispatch extraction from turn.py (separate follow-up)

## Verification

```bash
PYTHONPATH=src:. uv run -- python3 -m pytest -q tests/
PYTHONPATH=src:. uv run -- python3 -m py_compile $(find src -name '*.py')
uv lock --check
git diff --check
```

**Live validation:** `haxjobs chat --new` with DeepSeek — streaming sentences arrive complete, multi-turn tool calls work without 400 errors.

---

> **Warning for executor:** This plan replaces `model/client.py` with a profile-driven architecture. Before implementing, verify that `model/client.py:213` still only handles `delta.content` and that `agent_core/messages.py:34-45` still forbids extras on `AssistantMessage`. The plan is correct against commit `8f10995`. If either file has changed, reconcile first.
