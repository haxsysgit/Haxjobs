# Provider architecture findings — Hermes and Pi

## Result

- Complete. Hermes pattern studied in full. Pi is TypeScript and mostly compiled — not useful as a Python pattern source.
- Hermes uses a clean **declarative profile + plugin registration + hook-based customization** pattern. Pi uses a similar approach but in TypeScript.
- The current HaxJobs model layer (one `OpenAIModelClient` monolith) violates every design principle both codebases follow.
- Recommendation: copy Hermes' `ProviderProfile` + `build_api_kwargs_extras()` pattern into HaxJobs. Keep it simple — we have one provider today but the architecture must not be DeepSeek-shaped.

## Output

### Hermes provider architecture

**File tree:**
```
providers/
├── __init__.py        # registry: register_provider(), get_provider_profile(), _discover_providers()
├── base.py            # ProviderProfile dataclass — the core abstraction
└── README.md

plugins/model-providers/   # actual provider implementations (plugins)
├── deepseek/__init__.py   # DeepSeekProfile with thinking mode logic
├── anthropic/__init__.py  # AnthropicProfile with x-api-key auth
├── openai/__init__.py     # OpenAI profile
├── gemini/__init__.py     # Gemini profile
└── ... (20+ providers)
```

**The ProviderProfile dataclass** (`providers/base.py`):

A pure declarative struct. Does not own an HTTP client, does not make API calls, does not know about messages or tools. It describes the provider.

Key fields:
- `name`, `aliases` — identity and discovery
- `env_vars` — which env vars hold the API key
- `base_url` — OpenAI-compatible endpoint
- `auth_type` — api_key, oauth_device_code, etc.
- `default_max_tokens` — per-provider output cap
- `supports_vision`, `supports_health_check` — capability flags
- `fallback_models` — static model list when live fetch fails
- `default_headers` — provider-specific HTTP headers

Key hooks (overridable methods):
- `prepare_messages(messages)` — preprocess messages before sending (default: pass-through)
- `build_extra_body(**context)` — inject into `extra_body` (default: empty)
- `build_api_kwargs_extras(reasoning_config, model, **context)` — **the critical one**. Returns `(extra_body_dict, top_level_kwargs_dict)`. DeepSeek uses this to inject `extra_body.thinking` + `reasoning_effort`.

**The registry** (`providers/__init__.py`):

Lazy discovery pattern. First call to `get_provider_profile()` scans:
1. Bundled plugins at `plugins/model-providers/<name>/`
2. User plugins at `$HERMES_HOME/plugins/model-providers/<name>/`
3. Legacy single-file providers at `providers/<name>.py`

Each plugin imports and calls `register_provider(profile)`. User plugins override bundled on name collision. The registry maps name + aliases to profiles.

**How the transport uses it** (conversation_loop.py):

```python
profile = get_provider_profile(provider_name)  # or None
if profile:
    extra_body, top_level = profile.build_api_kwargs_extras(
        reasoning_config=reasoning_config,
        model=model_id,
    )
    kwargs["extra_body"].update(extra_body)
    kwargs.update(top_level)
```

If no profile matches, falls back to generic OpenAI-compatible behavior. The transport never hardcodes provider-specific logic.

**The DeepSeek plugin** (`plugins/model-providers/deepseek/__init__.py`):

A clean 65-line file. The entire provider-specific logic is:

1. `_model_supports_thinking(model)` — checks if this is a V4+ model (deepseek-v4-* or deepseek-reasoner). V3 and unknown models get no thinking mode injection.
2. `DeepSeekProfile.build_api_kwargs_extras()` — overrides the base hook to inject:
   - `extra_body["thinking"] = {"type": "enabled"|"disabled"}`
   - Top-level `reasoning_effort` from reasoning_config (low/medium/high/max)
3. A module-level `deepseek` instance with name, aliases, env_vars, base_url, fallback_models
4. `register_provider(deepseek)` at module level

That's it. The profile does not import OpenAI, does not touch messages, does not handle streaming. It just declares what makes DeepSeek different.

### Key design decisions to steal

1. **Declarative profile, not imperative adapter.** The profile says what's different. The transport applies it. This means the transport stays generic and new providers are a 40-line plugin file.

2. **Hook method, not a flag list.** `build_api_kwargs_extras()` is the single extension point. Providers that need nothing special don't override it. Providers that need custom headers, auth, message preprocessing — they override the relevant hook. No 20-field boolean flag soup.

3. **Thinking mode is a provider concern, not a model parameter.** DeepSeek's reasoning_effort and thinking toggle live entirely inside `DeepSeekProfile.build_api_kwargs_extras()`. The agent loop never mentions "thinking" or "reasoning_effort". The reasoning_config dict flows from user config → transport → profile hook.

4. **One class per provider, one file per provider.** No `if provider == "deepseek": do_x` anywhere outside the plugin file. The transport calls `profile.build_api_kwargs_extras()` and trusts the profile.

### What HaxJobs should build (not copy, adapt)

Hermes is 500K+ lines. HaxJobs needs maybe 200 lines. The adapted design:

```
model/
├── types.py           # unchanged
├── errors.py          # unchanged
├── protocol.py        # ModelClient protocol (extracted from client.py)
├── schemas.py         # tool schema conversion
├── profiles.py        # ProviderProfile dataclass + registry (NEW — Hermes pattern)
├── adapters/
│   ├── __init__.py
│   └── openai_compat.py  # Generic OpenAI-compatible adapter (replaces client.py)
├── profiles/              # Provider-specific profile plugins (NEW)
│   ├── __init__.py
│   └── deepseek.py        # DeepSeekProfile — thinking mode + reasoning_effort
├── provider.py         # ProviderConfig from haxjobs.toml (extracted from client.py)
└── fake.py             # unchanged
```

The pattern:

```python
# model/profiles.py
@dataclass
class ProviderProfile:
    name: str
    aliases: tuple[str, ...] = ()
    base_url: str = ""
    default_max_tokens: int | None = None

    def build_extra_body(self, *, model: str = "", **context) -> dict:
        return {}

    def build_api_kwargs(self, *, model: str = "", **context) -> dict:
        return {}

# model/profiles/deepseek.py
class DeepSeekProfile(ProviderProfile):
    def build_extra_body(self, *, model: str = "", **context) -> dict:
        if not model.startswith("deepseek-v4"):
            return {}
        return {"thinking": {"type": "enabled"}}

    def build_api_kwargs(self, *, model: str = "", **context) -> dict:
        return {"reasoning_effort": "high"}

deepseek = DeepSeekProfile(
    name="deepseek",
    aliases=("deepseek-chat", "deepseek-reasoner"),
    base_url="https://api.deepseek.com/v1",
)
register_profile(deepseek)

# model/adapters/openai_compat.py
class OpenAICompatAdapter:
    def __init__(self, config: ProviderConfig):
        profile = get_profile(config.provider_name)  # None → generic behavior
        self._profile = profile
        self._client = AsyncOpenAI(api_key=config.api_key, base_url=config.base_url)

    def _build_request_kwargs(self, request: ModelRequest) -> dict:
        kwargs = { ... }  # messages, tools, max_tokens, stream_options
        if self._profile:
            kwargs.setdefault("extra_body", {}).update(
                self._profile.build_extra_body(model=self._model)
            )
            kwargs.update(self._profile.build_api_kwargs(model=self._model))
        return kwargs
```

### Why this matters for the streaming bug

The current fix attempt in Plan 010 was wrong because it put thinking mode directly into `OpenAIModelClient._build_request_body()` with an `if self._provider == "deepseek"` gate. That's exactly the pattern Hermes avoids — provider-specific branches scattered in the transport.

The correct fix: 
1. Extract `ProviderProfile` dataclass + registry
2. Create `DeepSeekProfile` with `build_extra_body({"thinking": {"type": "enabled"}})` 
3. The adapter calls `profile.build_extra_body()` without knowing it's DeepSeek
4. `reasoning_content` handling stays in the adapter (it's a response-handling concern, not a request one) — but as a method on the adapter, not an if-check

## Evidence

- **Hermes ProviderProfile:** `/home/hax/.hermes/hermes-agent/providers/base.py` — 163-line dataclass with name, aliases, env_vars, base_url, auth_type, default_max_tokens, supports_vision, fallback_models, default_headers + hooks prepare_messages(), build_extra_body(), build_api_kwargs_extras(), get_max_tokens(), fetch_models()
- **Hermes registry:** `/home/hax/.hermes/hermes-agent/providers/__init__.py` — `register_provider()`, `get_provider_profile()`, `list_providers()`, lazy `_discover_providers()` scanning bundled + user + legacy plugin dirs
- **Hermes DeepSeek plugin:** `/home/hax/.hermes/hermes-agent/plugins/model-providers/deepseek/__init__.py` — 85 lines. DeepSeekProfile subclass, `build_api_kwargs_extras()` injects thinking mode + reasoning_effort only for V4+ models, module-level instance + register call
- **HaxJobs current client:** `/home/hax/haxjobs/src/haxjobs/model/client.py:36-56, 70-85, 120-230` — one class with six concerns. Provider config, client construction, complete(), stream(), tool schema conversion, error wrapping all in one file.
- **Pi architecture:** TypeScript, compiled, npm-packaged. Not a usable Python pattern source. Pi's TUI patterns were studied earlier.

## Learnings

- **Learning:** Hermes' provider plugin pattern means adding a new provider is one 40-85 line file with zero changes to the transport or agent loop.
  **Evidence:** `/home/hax/.hermes/hermes-agent/plugins/model-providers/` — 20+ provider directories, each a single `__init__.py`. The transport (`conversation_loop.py`) imports `get_provider_profile()` and calls the same hooks regardless of provider.
  **Reuse when:** Adding support for Anthropic, OpenAI, or any new provider — or when evaluating whether a framework will force you to change the agent loop for new providers.

- **Learning:** Provider-specific request parameters belong in a profile hook, never in `if provider == "x"` branches inside the transport.
  **Evidence:** Hermes' DeepSeek plugin puts thinking mode entirely in `build_api_kwargs_extras()`. HaxJobs' current code has no such separation — adding thinking mode would require adding a DeepSeek branch to client.py.
  **Reuse when:** Any time a new provider needs a different request shape (different auth, different extra_body format, different parameter names). The hook pattern localizes the change.

- **Learning:** ProviderProfile is a pure declarative dataclass — it does not own an HTTP client, does not import OpenAI, does not know about messages.
  **Evidence:** `providers/base.py` imports only `dataclasses`, `logging`, `typing`, and `urllib` (for model fetch). Zero LLM SDK imports.
  **Reuse when:** Designing any new abstraction for the model boundary. Pydantic models should own data shapes. The profile should own provider differences. The adapter should own the API call.
