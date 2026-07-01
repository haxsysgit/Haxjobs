# Hermes Agent — HaxJobs Integration Research

**Date**: 2026-06-30  
**Version researched**: 0.17.0 (installed via `/home/hax/.hermes/hermes-agent/venv/lib/python3.11/site-packages/hermes_agent-0.17.0.dist-info`)  
**Source**: Local installation at `/home/hax/.hermes/hermes-agent/` + GitHub `NousResearch/hermes-agent` (MIT, last updated 2026-06-30T18:37:40Z)  
**Language**: Python  
**Researcher**: Pi Coding Agent (Claude model) via direct source inspection

---

## Executive Summary

Hermes is the **only coding agent with a native Python API** suitable for direct in-process use by HaxJobs. Every other agent requires subprocess calls. Hermes offers two clean integration paths:

1. **Native mode** (HaxJobs running inside Hermes): `from agent.oneshot import run_oneshot` — zero subprocess overhead, direct Python function call.
2. **External mode** (cron/standalone): `hermes -z "prompt" --model <slug>` — subprocess, returns plain text.

Hermes has a sophisticated provider resolution chain that auto-falls-back through 7+ providers on rate-limit/credit-exhaustion (HTTP 402/429), making it the most resilient evaluation backend available.

---

## 1. Native Python API (In-Process)

### 1.1 Primary entry point: `agent.oneshot.run_oneshot()`

**File**: `/home/hax/.hermes/hermes-agent/agent/oneshot.py`  
**Lines**: 1–120

```python
from agent.oneshot import run_oneshot

result = run_oneshot(
    instructions="You are a job fit evaluator. Score the candidate against the JD...",
    user_input=f"JOB DESCRIPTION:\n{jd}\n\nCANDIDATE PROFILE:\n{profile}",
    task="title_generation",   # uses cheap/fast model by default
    max_tokens=2048,
    temperature=0.3,
    timeout=120.0,
    # main_runtime=...  # optionally inherit a live session's provider/model
)
```

Key parameters:
- `instructions` + `user_input`: system prompt + user message
- `task`: which auxiliary task config to use (defaults to `title_generation` — a cheap model)
- `max_tokens`: output limit (default 1024)
- `temperature`: 0.0–2.0 (default 0.3)
- `timeout`: seconds (default 60.0)
- `main_runtime`: dict with `api_key`, `base_url`, `provider`, `api_mode` — lets you inherit a live session's provider

Returns: `str` — plain text response, stripped of code fences.

### 1.2 Lower-level entry point: `agent.auxiliary_client.call_llm()`

**File**: `/home/hax/.hermes/hermes-agent/agent/auxiliary_client.py`  
**Lines**: 5568–5718

```python
from agent.auxiliary_client import call_llm

response = call_llm(
    task="title_generation",
    messages=[
        {"role": "system", "content": instructions},
        {"role": "user", "content": user_input},
    ],
    max_tokens=2048,
    temperature=0.3,
    timeout=120.0,
)
# response.choices[0].message.content  ← the text
```

This gives full control over messages, tools, extra_body. `run_oneshot` is a convenience wrapper around `call_llm`.

### 1.3 Import path for HaxJobs

When HaxJobs runs inside Hermes, the agent package is already on `sys.path`:

```python
# No sys.path manipulation needed — hermes-agent is the running process
from agent.oneshot import run_oneshot
```

When HaxJobs runs standalone (cron on Archilles), the venv must be activated or `sys.path` adjusted:

```python
import sys
sys.path.insert(0, "/home/hermes/.hermes/hermes-agent")
sys.path.insert(0, "/home/hermes/.hermes/hermes-agent/venv/lib/python3.11/site-packages")
from agent.oneshot import run_oneshot
```

---

## 2. Headless CLI Mode (`hermes -z`)

### 2.1 CLI entry point

**File**: `/home/hax/.hermes/hermes-agent/hermes_cli/oneshot.py` (lines 1–400)

```bash
hermes -z "Evaluate this job..." --model gpt-5.5
hermes -z "prompt" --model deepseek/deepseek-v4-pro --provider openrouter
```

Flags:
- `-z` / `--oneshot`: headless mode, prints ONLY the final response to stdout
- `--model <slug>`: model slug (e.g., `gpt-5.5`, `deepseek/deepseek-v4-pro`)
- `--provider <id>`: provider override (requires `--model` too)
- `--toolsets <name>`: comma-separated toolset list (optional)

Behavior:
- Auto-bypasses approvals (`HERMES_YOLO_MODE=1`, `HERMES_ACCEPT_HOOKS=1`)
- Redirects all stderr/stdout to /dev/null during execution
- Only prints final response text to real stdout
- Exit codes: 0 = success, 1 = failure, 2 = invalid args

### 2.2 Model resolution order

From `hermes_cli/oneshot.py` lines 140–170:

1. `--model` CLI flag
2. `HERMES_INFERENCE_MODEL` env var
3. `config.yaml` → `model.default` or `model.model`

Provider resolution:
1. `--provider` CLI flag
2. Auto-detected from model slug via `detect_provider_for_model()` in `hermes_cli/models.py:1918`
3. `config.yaml` → `model.provider`
4. `HERMES_INFERENCE_PROVIDER` env var
5. `"auto"` (triggers full provider detection chain)

### 2.3 Subprocess invocation from HaxJobs

```python
import subprocess, json

result = subprocess.run(
    ["hermes", "-z", prompt,
     "--model", "gpt-5.5"],
    capture_output=True, text=True, timeout=180
)
if result.returncode == 0:
    return result.stdout.strip()
```

---

## 3. Model Discovery & Provider Registry

### 3.1 Current configuration

From `~/.hermes/config.yaml` (read 2026-06-30):

```yaml
model:
  default: gpt-5.5
  provider: openai-codex
  base_url: https://api.xiaomimimo.com/v1
```

- Primary model: `gpt-5.5` via `openai-codex` (ChatGPT OAuth)
- Fallback base_url: Xiaomi Mimo API (for auxiliary tasks)

### 3.2 Provider registry

**File**: `/home/hax/.hermes/hermes-agent/hermes_cli/providers.py` (lines 1–700+)

Key functions:
- `get_provider(name)` → `ProviderDef | None` — lookup by ID
- `list_authenticated_providers()` in `model_switch.py:1407` — returns providers with valid auth
- `list_picker_providers()` in `model_switch.py:2262` — returns provider list for UI picker
- `detect_provider_for_model(model_slug, current_provider)` in `models.py:1918` — auto-maps model slug to provider

Provider aliases (from `auxiliary_client.py` lines 575–601):

```python
_PROVIDER_ALIASES = {
    "google": "gemini", "claude": "anthropic", "github": "copilot",
    "x-ai": "xai", "grok": "xai", "glm": "zai", "kimi": "kimi-coding",
    "moonshot": "kimi-coding", "minimax-china": "minimax-cn", ...
}
```

### 3.3 Auxiliary model defaults per provider

From `agent/auxiliary_client.py` lines 647–665:

```python
_API_KEY_PROVIDER_AUX_MODELS = {
    "gemini": "gemini-3-flash-preview",
    "zai": "glm-4.5-flash",
    "kimi-coding": "kimi-k2-turbo-preview",
    "anthropic": "claude-haiku-4-5-20251001",
    "opencode-zen": "gemini-3-flash",
    "opencode-go": "glm-5",
    "kilocode": "google/gemini-3-flash-preview",
    ...
}
```

### 3.4 Reading model list from HaxJobs

```python
# Method 1: Parse config.yaml directly
import yaml
with open(os.path.expanduser("~/.hermes/config.yaml")) as f:
    cfg = yaml.safe_load(f)
default_model = cfg["model"]["default"]  # "gpt-5.5"
default_provider = cfg["model"]["provider"]  # "openai-codex"

# Method 2: Full provider list (only when inside Hermes process)
from hermes_cli.model_switch import list_authenticated_providers
providers = list_authenticated_providers()
# Returns list of (provider_id, display_name, models_list)
```

---

## 4. Rate Limit Detection & Model Switching

### 4.1 Automatic fallback chain

**File**: `/home/hax/.hermes/hermes-agent/agent/auxiliary_client.py` lines 5650–5750

Hermes has **built-in multi-provider fallback** on HTTP 402 (payment required) and credit exhaustion errors. The resolution order for auto-mode text tasks:

1. User's main provider + main model (currently: `openai-codex` with `gpt-5.5`)
2. OpenRouter (`OPENROUTER_API_KEY`)
3. Nous Portal (`~/.hermes/auth.json` active provider)
4. Custom endpoint (`config.yaml model.base_url + OPENAI_API_KEY`)
5. Native Anthropic
6. Direct API-key providers (z.ai/GLM, Kimi/Moonshot, MiniMax, MiniMax-CN)
7. None (raises RuntimeError)

### 4.2 Rate limit detection in output

Hermes' subprocess mode `hermes -z` will produce error text in stdout when rate-limited. From our existing `evaluate/agents/hermes.py` pattern:

```python
def _is_rate_limited(output: str) -> bool:
    markers = ["HTTP 429", "usage limit", "rate limit", "quota exceeded",
               "rate_limit_exceeded", "too many requests"]
    output_lower = output.lower()
    return any(m in output_lower for m in markers)
```

### 4.3 Explicit model switching

**From HaxJobs evaluate/agents/hermes.py** (already implemented):

```python
def call_agent(prompt, timeout_seconds=180, retries=0):
    models = ["gpt-5.5", "deepseek/deepseek-v4-pro", "openai/gpt-4o"]
    for model in models:
        result = subprocess.run(
            ["hermes", "-z", prompt, "--model", model],
            capture_output=True, text=True, timeout=timeout_seconds
        )
        output = result.stdout.strip()
        if result.returncode == 0 and not _is_rate_limited(output):
            return output  # success
        # else: try next model
    return None
```

### 4.4 Native mode: trust Hermes' own fallback

When using the native API (`run_oneshot`), Hermes handles provider fallback internally. The caller just needs to catch `RuntimeError("No LLM provider configured")` as the terminal failure signal:

```python
try:
    result = run_oneshot(instructions=..., user_input=..., timeout=120)
except RuntimeError as e:
    if "No LLM provider configured" in str(e):
        return None  # all providers exhausted
    raise
```

---

## 5. Config File Format

### 5.1 Location

`~/.hermes/config.yaml` — standard YAML, loaded by `hermes_cli/config.py`.

### 5.2 Relevant sections for HaxJobs

```yaml
model:
  default: gpt-5.5          # primary model slug
  provider: openai-codex     # primary provider
  base_url: https://...      # optional custom endpoint

providers: {}                # custom provider definitions

fallback_providers: []       # explicit fallback chain

auxiliary:
  title_generation:
    provider: auto
    model: ""                # empty = use provider's cheap default
    timeout: 30
  compression:
    provider: auto
    model: ""
    timeout: 120
```

### 5.3 Adding a HaxJobs-specific auxiliary task

Hermes supports adding custom auxiliary task configs. HaxJobs could define:

```yaml
auxiliary:
  haxjobs_evaluation:
    provider: auto
    model: "gpt-5.5"         # explicit model for evaluation
    timeout: 180
    temperature: 0.3
```

Then from native code:

```python
run_oneshot(task="haxjobs_evaluation", instructions=..., user_input=...)
```

---

## 6. Integration Assessment

### 6.1 Integration difficulty: ⭐ TRIVIAL

Hermes is the gold-standard integration target. It's Python, fully importable, and already has the exact abstraction HaxJobs needs (`run_oneshot`).

### 6.2 Recommended HaxJobs adapter

**File**: `evaluate/agents/hermes.py` (already exists, needs native-mode upgrade)

Two-mode adapter:

```python
def call_agent(prompt, timeout_seconds=180, retries=0):
    """Try native import first, fall back to subprocess."""
    try:
        from agent.oneshot import run_oneshot
        return run_oneshot(
            instructions="You are a job fit evaluator...",
            user_input=prompt,
            max_tokens=2048,
            temperature=0.3,
            timeout=timeout_seconds,
        )
    except ImportError:
        pass  # not running inside Hermes
    
    # External mode: subprocess
    models = _get_available_models()
    for model in models:
        result = subprocess.run(
            ["hermes", "-z", prompt, "--model", model],
            capture_output=True, text=True, timeout=timeout_seconds
        )
        if result.returncode == 0 and not _is_rate_limited(result.stdout):
            return result.stdout.strip()
    return None

def _get_available_models():
    """Read model list from ~/.hermes/config.yaml"""
    import yaml
    cfg = yaml.safe_load(open(os.path.expanduser("~/.hermes/config.yaml")))
    default = cfg["model"]["default"]
    # Build fallback chain: default → common alternatives
    return [default, "deepseek/deepseek-v4-pro", "openai/gpt-4o",
            "google/gemini-2.5-flash", "anthropic/claude-sonnet-4"]
```

### 6.3 Shipping HaxJobs to Hermes users

Hermes has a plugin system (`hermes_cli/plugins.py`, 85K). HaxJobs could ship as a Hermes plugin:

1. Create `~/.hermes/plugins/haxjobs/plugin.py`
2. Register slash commands: `/haxjobs evaluate`, `/haxjobs report`, `/haxjobs discover`
3. Hook into Hermes' agent session for native `run_oneshot` access

But this is **not required** for the automated pipeline. The plugin is nice-to-have for interactive use; the evaluate/ adapter handles cron evaluation.

---

## 7. Key Source Files Referenced

| File | Lines | Purpose |
|------|-------|---------|
| `agent/oneshot.py` | 120 | `run_oneshot()` — one-shot LLM call API |
| `agent/auxiliary_client.py` | 6,536 | `call_llm()` — centralized LLM router with provider fallback |
| `hermes_cli/oneshot.py` | 400 | CLI `-z` mode — headless subprocess entry |
| `hermes_cli/models.py` | 4,200+ | `detect_provider_for_model()`, model listing |
| `hermes_cli/providers.py` | 700+ | `ProviderDef`, `get_provider()`, provider registry |
| `hermes_cli/model_switch.py` | 2,500+ | Model switching, alias resolution |
| `hermes_cli/config.py` | 8,000+ | Config loading from `~/.hermes/config.yaml` |
| `hermes_cli/fallback_config.py` | ~60 | `get_fallback_chain()` for provider fallback |
| `agent/credential_pool.py` | — | Multi-key credential pooling with rotation |

All paths relative to `/home/hax/.hermes/hermes-agent/`.

---

## 8. Next Steps

1. **Upgrade `evaluate/agents/hermes.py`** to try native `run_oneshot` before subprocess fallback
2. **Add `_get_available_models()`** that reads `~/.hermes/config.yaml` for model discovery
3. **Remove blind model hardcoding** — use config-driven model list with `gpt-5.5` default
4. **Consider Hermes plugin** for interactive HaxJobs use (non-blocking — cron runs headless anyway)

---

*Research completed 2026-06-30. Source: direct inspection of Hermes 0.17.0 source tree at `/home/hax/.hermes/hermes-agent/`. All line numbers and function signatures verified against installed code.*
