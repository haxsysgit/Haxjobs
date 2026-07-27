# Plan 010 — Provider architecture: profiles, adapter, streaming fix

> **Baseline:** `8f10995` (current main)
> **Drift stamp:** 2026-07-26
> **Status:** ACCEPTED (architecture decision from Hermes study)
> **Depends on:** Plan 009 DONE

## Goal

Rebuild the model layer around Hermes' provider profile pattern — a declarative abstraction where each provider is a small plugin file, the adapter is a generic transport, and provider-specific behavior (thinking mode, reasoning_effort, auth) lives in profile hooks, never in `if provider == "deepseek"` branches. Fix the DeepSeek streaming bug as a natural consequence of properly modeling the provider boundary.

## Architecture decision

From the Hermes architecture study (`discussion/research/provider-architecture-hermes-study.md`):

1. **ProviderProfile** — pure declarative dataclass. Describes what makes a provider different. Does NOT own HTTP clients, does NOT import OpenAI, does NOT know about messages.

2. **Profile hooks** — `build_extra_body(model, **context) → dict` and `build_api_kwargs(model, **context) → dict`. The adapter calls these at request time. Providers that need nothing special don't override them.

3. **One file per provider, ~40-85 lines.** Adding Anthropic, OpenAI later means one new profile file with zero changes to the transport.

4. **The adapter is generic.** It reads the profile, applies the hooks, handles streaming/non-streaming, accumulates tool calls and reasoning, and exposes a provider-neutral interface. No provider branches.

---

## Current state — what must change

### `model/client.py` (300 lines, one class doing six things)

Must become:
- `model/protocol.py` — `ModelClient` protocol (extracted)
- `model/profiles/base.py` — `ProviderProfile` dataclass + `register_profile()` + `get_profile()`
- `model/profiles/__init__.py` — imports deepseek to trigger self-registration, re-exports from base
- `model/profiles/deepseek.py` — `DeepSeekProfile` (~50 lines, thinking mode + reasoning_effort)
- `model/adapters/openai_compat.py` — Generic adapter (~200 lines, replaces `OpenAIModelClient`)
- `model/schemas.py` — tool schema conversion (extracted from client.py duplicate code)
- `model/provider.py` — `ProviderConfig` dataclass (extracted from client.py inline TOML loading)

### `model/types.py`

Must add to support the provider abstraction:
- `THINKING_DELTA` to `ModelStreamEventType`
- `reasoning_content: str = ""` to `ModelResponse`

### `agent_core/messages.py`

Must add to support reasoning preservation:
- `reasoning_content: str = ""` field to `AssistantMessage`
- `_pending_reasoning_content` to `MessageProjector`
- Reasoning content carried through `_flush()` onto projected `ModelMessage`

### `agent_core/turn.py`

Must add:
- `accumulated_reasoning` inside the loop
- `THINKING_DELTA` branch in the stream handler
- Reasoning content set on both the canonical `AssistantMessage` and the direct in-loop `ModelMessage`

---

## Implementation

### Phase 1 — Provider infrastructure (3 new files, 2 changed)

**New files:**
- `model/protocol.py` — `ModelClient` protocol extracted from `client.py`
- `model/profiles/base.py` — `ProviderProfile` dataclass + `_REGISTRY` + `register_profile()`, `get_profile()`
- `model/profiles/__init__.py` — imports deepseek, re-exports from base
- `model/schemas.py` — `tool_schemas_to_provider(tools: list[ToolSchema]) → list[dict]` extracted from `client.py`

**Changed files:**
- `model/types.py` — add `THINKING_DELTA`, `reasoning_content` to `ModelResponse` and `ModelMessage`
- `model/__init__.py` — add exports for new modules, change `ModelClient` import to `protocol`

**ProviderProfile dataclass:**
```python
@dataclass
class ProviderProfile:
    name: str
    aliases: tuple[str, ...] = ()
    default_max_tokens: int | None = None

    def build_extra_body(self, *, model: str = "", **context) -> dict[str, Any]:
        return {}

    def build_api_kwargs(self, *, model: str = "", **context) -> dict[str, Any]:
        return {}
```

**Registry:**
- `_REGISTRY: dict[str, ProviderProfile] = {}`
- `_ALIASES: dict[str, str] = {}`
- `register_profile(profile)` — insert by name + aliases
- `get_profile(name)` — lookup by name or alias, returns None for generic

**Tests:** 5 tests — register + lookup by name, lookup by alias, get_profile returns None for unknown, build_extra_body default returns empty, build_api_kwargs default returns empty.

### Phase 2 — DeepSeek profile (1 new file)

**New file:**
- `model/profiles/deepseek.py` — `DeepSeekProfile`

```python
class DeepSeekProfile(ProviderProfile):
    def build_extra_body(self, *, model: str = "", **context) -> dict:
        if not model.startswith("deepseek-v4"):
            return {}
        return {"thinking": {"type": "enabled"}}

    def build_api_kwargs(self, *, model: str = "", **context) -> dict:
        if not model.startswith("deepseek-v4"):
            return {}
        return {"reasoning_effort": "high"}

# Module-level instance + self-registration
deepseek = DeepSeekProfile(
    name="deepseek",
    aliases=("deepseek-chat", "deepseek-reasoner"),
    base_url="https://api.deepseek.com/v1",
)
register_profile(deepseek)
```

Import at startup: `model/__init__.py` imports `model.profiles.deepseek` to trigger self-registration, or `model/profiles/__init__.py` does it. Hermes uses lazy discovery — for HaxJobs with one provider, eager import at `__init__.py` is simpler.

**Tests:** 2 tests — v4 model gets thinking + reasoning_effort, non-v4 model gets empty dicts.

### Phase 3 — Provider config extraction (1 new file, 1 changed)

**New file:**
- `model/provider.py` — `ProviderConfig` dataclass extracted from `client.py:36-56`

```python
@dataclass
class ProviderConfig:
    name: str
    model: str
    api_key: str
    base_url: str = "https://api.deepseek.com/v1"

    @classmethod
    def from_file(cls, path: Path) -> "ProviderConfig": ...
```

**Changed file:**
- `model/client.py` — delete inline TOML loading, import from `provider.py`

**Tests:** 3 tests — load from valid TOML, missing model key raises, missing api_key raises.

### Phase 4 — Generic OpenAI-compatible adapter (1 new file)

**New file:**
- `model/adapters/openai_compat.py` — replaces `OpenAIModelClient`

Constructor takes `ProviderConfig`. Gets profile via `get_profile(config.name)` (None → generic behavior). The adapter calls `profile.build_extra_body()` and `profile.build_api_kwargs()` in every request.

```python
class OpenAICompatAdapter:
    def __init__(self, config: ProviderConfig):
        self._config = config
        self._profile = get_profile(config.name)
        self._client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            max_retries=0,
        )

    def _build_kwargs(self, request: ModelRequest) -> dict:
        kwargs = {
            "model": self._config.model,
            "messages": [...],
            "max_tokens": request.max_tokens,
        }
        if request.tools:
            kwargs["tools"] = tool_schemas_to_provider(request.tools)

        # Apply profile hooks
        if self._profile:
            extra = self._profile.build_extra_body(model=self._config.model)
            if extra:
                kwargs.setdefault("extra_body", {}).update(extra)
            kwargs.update(self._profile.build_api_kwargs(model=self._config.model))

        return kwargs
```

**Stream method:** same logic as current `client.py` stream but adds:
- `reasoning_content` capture → `THINKING_DELTA` events
- Profile hooks applied via `_build_kwargs()`

**Complete method:** same as current but adds `reasoning_content` to `ModelResponse`.

**Changed files:**
- `model/__init__.py` — export `OpenAICompatAdapter` instead of `OpenAIModelClient`
- `employment/composition.py` — construct `OpenAICompatAdapter(ProviderConfig.from_file(PROVIDER_CONFIG_PATH))`
  instead of the no-arg `OpenAIModelClient()` call at line 72

**Deleted:** `model/client.py`. All imports of `ModelClient` move to `model.protocol`.
`agent_core/session.py`, `agent_core/turn.py`, and `model/fake.py` import
`ModelClient` from `client.py` — update these to `model.protocol`.

**Tests:**
- Adapter builds correct kwargs with DeepSeek profile (thinking + reasoning_effort in extra_body)
- Adapter builds correct kwargs without profile (no extra_body)
- Stream yields THINKING_DELTA for reasoning_content chunks
- Stream correctly accumulates tool calls
- Complete() captures reasoning_content in ModelResponse
- Cancellation handling unchanged

### Phase 5 — Reasoning preservation in messages and turn loop (2 changed)

**File: `agent_core/messages.py`**

- Add `reasoning_content: str = ""` to `AssistantMessage`
- Add `self._pending_reasoning_content = ""` to `MessageProjector.__init__`
- In `project()`, carry reasoning from `AssistantMessage` when present
- In `_flush()`, attach to projected `ModelMessage` if non-empty

**File: `agent_core/turn.py`**

- Add `accumulated_reasoning = ""` inside the loop alongside `accumulated_text`
- Add `THINKING_DELTA` branch: `accumulated_reasoning += stream_event.delta`
- Set `reasoning_content=accumulated_reasoning` on both:
  - The canonical `AssistantMessage` (persisted to history)
  - The direct in-loop `ModelMessage(role="assistant", tool_calls=...)` (immediate next request)

**Tests:**
- Fake-stream test: `fake.requests[1]` contains reasoning_content on assistant message with tool calls
- Multi-turn: first turn tool calls + reasoning, second turn projected messages include it
- Backward compat: AssistantMessage without reasoning_content parses correctly
- Thinking not leaked to LiveEvent

---

## Files in scope

| File | Change |
|---|---|
| `model/protocol.py` | New — ModelClient protocol extracted |
| `model/profiles/base.py` | New — ProviderProfile + registry |
| `model/profiles/__init__.py` | New — imports deepseek, re-exports base |
| `model/profiles/deepseek.py` | New — DeepSeekProfile |
| `model/schemas.py` | New — tool schema conversion |
| `model/provider.py` | New — ProviderConfig |
| `model/adapters/__init__.py` | New |
| `model/adapters/openai_compat.py` | New — generic adapter (replaces client.py) |
| `model/client.py` | Deleted |
| `model/types.py` | THINKING_DELTA + reasoning_content on ModelResponse and ModelMessage |
| `model/__init__.py` | Updated exports |
| `model/fake.py` | Update ModelClient import to protocol |
| `agent_core/session.py` | Update ModelClient import to protocol |
| `agent_core/turn.py` | Accumulate reasoning, THINKING_DELTA branch, set on both message paths |
| `agent_core/messages.py` | reasoning_content on AssistantMessage, projector carries it |
| `employment/composition.py` | Construct OpenAICompatAdapter from ProviderConfig |
| `tests/` | New tests for all new modules |

## Files NOT touched

- `agent_core/session.py`
- `agent_core/live_events.py`
- `agent_core/session.py` (ModelClient import update only)
- `agent_core/tools.py`
- `agent_core/dispatch.py`
- `employment/*` (except composition.py wire-up)
- `interfaces/*`
- `model/fake.py`
- `model/errors.py`

## Verification

```bash
PYTHONPATH=src:. uv run -- python3 -m pytest -q tests/
PYTHONPATH=src:. uv run -- python3 -m py_compile $(find src -name '*.py')
uv lock --check
git diff --check
```

**Live validation:** `haxjobs chat --new` — streaming works, sentences complete, multi-turn tool calls don't break.

## Out of scope

- user_id context caching (separate follow-up)
- Token usage tracking improvements
- Anthropic API format adapter (future profile plugin)
- TUI thinking indicator
- Reasoning effort user configuration (hardcoded "high" for now)
- Provider fallback cascade
- Live model catalog fetching

---

> **Warning for executor:** This plan introduces 8 new files and deletes 1. The `ModelClient` protocol moves from `client.py` to `protocol.py` — update every import. `employment/composition.py` is the only employment file touched and only for the adapter class name change. Verify no stale `from haxjobs.model.client import OpenAIModelClient` remains anywhere.
