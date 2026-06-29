# Plan 029: Build model-aware multi-agent evaluation with native integration

> **Executor**: This plan builds the production evaluation adapters based on Plan 027 research and Plan 028 test results. The architecture is fundamentally different from the shallow approach: adapters prioritize NATIVE integration (direct function calls into the agent's Python API) over EXTERNAL (subprocess). Every adapter is model-aware: it reads the agent's config and knows which models are available.
>
> **Drift check**: `test -f research/test-results/SUMMARY.md && echo "Plan 028 done" || echo "BLOCKED: Plan 028 not complete"` — confirms Plan 028 testing is done.

## Status

- **Priority**: P1
- **Effort**: L (6-10 hours, includes building adapters, rewriting evaluate/run.py, and testing)
- **Risk**: MED (native APIs may be fragile across agent versions; need good error handling)
- **Depends on**: Plan 027 + Plan 028
- **Category**: feature
- **Planned at**: commit `354429b`, 2026-06-29

## Why this matters

After Plans 027-028, we know:
- Which agents have importable Python APIs (native mode)
- Which agents support multiple models (model switching)
- Which models work and what their latency/quality is
- The exact function calls and import paths

Plan 029 builds adapters that use the DEEPEST integration available:

| Agent | Best integration | Fallback |
|-------|-----------------|----------|
| Hermes | `from hermes_cli.xxx import yyy` — direct function call | `subprocess: hermes chat --yolo -Q -q --model X` |
| Claude API | `urllib.request` → Anthropic Messages API | N/A (always API) |
| Gemini API | `urllib.request` → Google Generative Language API | N/A (always API) |
| Codex (if native) | `import codex` — direct function call | `subprocess: codex exec` |
| Pi | Pi extension registering `haxjobs_evaluate` tool | Pi skill (interactive only) |

## Architecture

```
evaluate/
├── agents/
│   ├── __init__.py           # AGENT_REGISTRY dict
│   ├── hermes.py             # REWRITTEN — native import + config reading + model switching
│   ├── claude_api.py         # NEW — direct Anthropic Messages API (stdlib)
│   ├── gemini_api.py         # NEW — direct Google Gemini API (stdlib)
│   ├── codex.py              # NEW — if native API found in 027/028
│   ├── claude_code.py        # NEW — if native API found in 027/028
│   └── gemini.py             # NEW — if native API found in 027/028
├── common.py                 # UNCHANGED — build_prompt, extract_json, validate_result
├── run.py                    # REWRITTEN — model-aware agent dispatch
└── model_registry.py         # NEW — reads agent configs, manages fallback chains
```

### New file: `evaluate/model_registry.py`

Central module that reads agent configs and manages model availability:

```python
"""Model registry — reads agent configs, tracks availability, manages fallback chains."""

import os
import json
import time
from typing import Optional

# Per-model rate-limit tracking
_rate_limit_state: dict[str, float] = {}  # model_key → timestamp when rate-limited


def is_rate_limited(model_key: str, cooldown_seconds: int = 300) -> bool:
    """Check if a model is currently in rate-limit cooldown."""
    if model_key in _rate_limit_state:
        elapsed = time.time() - _rate_limit_state[model_key]
        if elapsed < cooldown_seconds:
            return True
        del _rate_limit_state[model_key]
    return False


def mark_rate_limited(model_key: str) -> None:
    """Record that a model hit a rate limit."""
    _rate_limit_state[model_key] = time.time()


def get_hermes_models() -> list[dict]:
    """Read Hermes config.yaml and return available models in priority order."""
    # Attempt 1: import hermes_cli directly
    try:
        from hermes_cli.config import load_config
        cfg = load_config()
        models = cfg.get("models", [])
        if models:
            return models
    except ImportError:
        pass
    
    # Attempt 2: parse config.yaml manually
    yaml_path = os.path.expanduser("~/.hermes/hermes-agent/config.yaml")
    if os.path.exists(yaml_path):
        return _parse_hermes_yaml_models(yaml_path)
    
    return []


def get_available_models() -> dict[str, list[str]]:
    """Return {agent_name: [model_keys]} for the configured agent."""
    agent = os.environ.get("HAXJOBS_EVALUATION_AGENT", "hermes")
    if agent == "hermes":
        models = get_hermes_models()
        return {"hermes": [f"{m['provider']}/{m['name']}" for m in models]}
    # ... other agents
    return {}


def select_model(agent_name: str, preferred: str | None = None) -> str | None:
    """Pick the best available model for an agent, skipping rate-limited ones."""
    models = get_available_models().get(agent_name, [])
    
    # Try preferred model first
    if preferred and preferred in models and not is_rate_limited(preferred):
        return preferred
    
    # Try each model
    for model in models:
        if not is_rate_limited(model):
            return model
    
    return None
```

### Rewritten: `evaluate/agents/hermes.py`

```python
"""Hermes adapter — native integration with hermes_cli Python API.

Uses direct function calls when running inside Hermes (no subprocess).
Reads config.yaml to know available models.
Switches models automatically when rate-limited.

External mode (cron/subprocess): calls hermes chat CLI with explicit --model flag.
"""

import os
import subprocess
import sys
import time
from evaluate.model_registry import is_rate_limited, mark_rate_limited, get_hermes_models

# ---- Config ----
HERMES_CONFIG_PATH = os.path.expanduser("~/.hermes/hermes-agent/config.yaml")


def _detect_inside_hermes() -> bool:
    """Are we running inside a Hermes process?"""
    return bool(os.environ.get("HERMES_SESSION_ID") or os.environ.get("HERMES_HOME"))


def _native_call(prompt: str, model: str = "deepseek", timeout: int = 180) -> str | None:
    """Call Hermes model directly via Python API — NO subprocess."""
    try:
        # ponytail: hermes_cli may not be on PYTHONPATH from HaxJobs venv.
        # We add Hermes' venv to sys.path if needed.
        hermes_path = os.path.expanduser("~/.hermes/hermes-agent")
        if hermes_path not in sys.path:
            sys.path.insert(0, hermes_path)
        
        from hermes_cli.xxx import yyy  # Exact import from Plan 027 research
        result = yyy(prompt, model=model, max_tokens=4096)
        return result
    except ImportError as e:
        # hermes_cli not importable — fall back to external
        return None
    except Exception as e:
        if "rate" in str(e).lower() or "429" in str(e):
            mark_rate_limited(f"hermes/{model}")
        return None


def _external_call(prompt: str, model: str = "deepseek", timeout: int = 180) -> str | None:
    """Call Hermes via CLI subprocess — used when native import fails."""
    try:
        result = subprocess.run(
            ["hermes", "chat", "--yolo", "-Q", "-q", "--model", model, prompt],
            capture_output=True, text=True, timeout=timeout,
            env={**os.environ, "HOME": os.path.expanduser("~")},
        )
        output = result.stdout.strip()
        if not output:
            return None
        if "rate limit" in output.lower() or "usage limit" in output.lower():
            mark_rate_limited(f"hermes/{model}")
            return None
        return output
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def call_agent(prompt: str, *, timeout_seconds: int = 180, retries: int = 2) -> str | None:
    """Send prompt to Hermes. Native mode preferred, external as fallback."""
    
    # Get available models from config (sorted by priority)
    models = get_hermes_models()
    model_keys = [f"{m.get('provider','')}/{m.get('name','')}" for m in models]
    
    if not model_keys:
        model_keys = ["deepseek"]  # fallback default
    
    use_native = _detect_inside_hermes()
    
    for model_key in model_keys:
        if is_rate_limited(model_key):
            continue
        
        for attempt in range(retries + 1):
            if use_native:
                result = _native_call(prompt, model=model_key, timeout=timeout_seconds)
            else:
                result = _external_call(prompt, model=model_key, timeout=timeout_seconds)
            
            if result:
                return result
            
            if attempt < retries:
                time.sleep(2 ** attempt)
    
    return None
```

### New file: `evaluate/agents/claude_api.py`

```python
"""Claude API adapter — direct Anthropic Messages API via stdlib."""

import json
import os
import urllib.request
import urllib.error

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-3-5-sonnet-20241022"  # ponytail: single model, configurable via env
MAX_TOKENS = 4096


def _api_key() -> str:
    return os.environ.get("ANTHROPIC_API_KEY", "")


def call_agent(prompt: str, *, timeout_seconds: int = 180, retries: int = 2) -> str | None:
    key = _api_key()
    if not key:
        return None

    payload = json.dumps({
        "model": os.environ.get("HAXJOBS_CLAUDE_MODEL", MODEL),
        "max_tokens": int(os.environ.get("HAXJOBS_CLAUDE_MAX_TOKENS", str(MAX_TOKENS))),
        "messages": [{"role": "user", "content": prompt}],
    }).encode()

    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(API_URL, data=payload, headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            })
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                data = json.loads(resp.read())
                # Extract text from content block
                for block in data.get("content", []):
                    if block.get("type") == "text":
                        return block["text"]
                return None
        except urllib.error.HTTPError as e:
            if e.code == 429:
                return None  # rate limited
            if attempt == retries:
                return None
        except Exception:
            if attempt == retries:
                return None
    return None
```

### New file: `evaluate/agents/gemini_api.py`

Same pattern as Claude API but against Google Generative Language API.

```python
"""Gemini API adapter — direct Google Generative Language API via stdlib."""

import json
import os
import urllib.request
import urllib.error

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
MODEL = "gemini-2.5-flash"


def _api_key() -> str:
    return os.environ.get("GEMINI_API_KEY", "")


def call_agent(prompt: str, *, timeout_seconds: int = 180, retries: int = 2) -> str | None:
    key = _api_key()
    if not key:
        return None

    model = os.environ.get("HAXJOBS_GEMINI_MODEL", MODEL)
    url = f"{API_BASE}/{model}:generateContent?key={key}"
    
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",  # Gemini native JSON mode!
        },
    }).encode()

    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, data=payload, headers={
                "Content-Type": "application/json",
            })
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                data = json.loads(resp.read())
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "")
                return None
        except urllib.error.HTTPError as e:
            if e.code == 429:
                return None
            if attempt == retries:
                return None
        except Exception:
            if attempt == retries:
                return None
    return None
```

## Steps

### Step 1: Create `evaluate/model_registry.py`

Implement as specified above. Core functions:
- `get_hermes_models()` — reads config.yaml, returns model list with provider/priority
- `is_rate_limited(model_key)` / `mark_rate_limited(model_key)` — cooldown tracking
- `select_model(agent_name)` — picks best available model, skipping rate-limited ones

**Verify**:
```bash
PYTHONPATH=. python3 -c "
from evaluate.model_registry import get_hermes_models, select_model
models = get_hermes_models()
print(f'Hermes models: {len(models)}')
for m in models:
    print(f'  {m}')
model = select_model('hermes')
print(f'Selected: {model}')
"
```

### Step 2: Rewrite `evaluate/agents/hermes.py`

Replace the current shallow subprocess-only adapter with the native+external version above.

Key additions:
- `_detect_inside_hermes()` — check env vars
- `_native_call()` — direct Python import (exact import from Plan 027)
- `_external_call()` — subprocess with explicit `--model` flag
- Model switching from `model_registry`

**Verify**:
```bash
# Import test
PYTHONPATH=. python3 -c "from evaluate.agents.hermes import call_agent; print('Import OK')"

# Model list test
PYTHONPATH=. python3 -c "
from evaluate.agents.hermes import call_agent
from evaluate.model_registry import get_hermes_models
print('Models:', get_hermes_models())
"
```

### Step 3: Create `evaluate/agents/claude_api.py` + `evaluate/agents/gemini_api.py`

Implement as specified above. Pure stdlib, no dependencies.

**Verify**:
```bash
PYTHONPATH=. python3 -c "from evaluate.agents.claude_api import call_agent; print('Claude API import OK')"
PYTHONPATH=. python3 -c "from evaluate.agents.gemini_api import call_agent; print('Gemini API import OK')"
```

### Step 4: Update `evaluate/agents/__init__.py`

```python
"""HaxJobs evaluation agent adapters.

Each module exports a call_agent(prompt, *, timeout_seconds, retries) -> str | None function.
"""

from evaluate.agents.hermes import call_agent as hermes_call_agent

# Optional adapters — may fail to import if not configured
try:
    from evaluate.agents.claude_api import call_agent as claude_api_call_agent
except ImportError:
    claude_api_call_agent = None

try:
    from evaluate.agents.gemini_api import call_agent as gemini_api_call_agent
except ImportError:
    gemini_api_call_agent = None

AGENT_REGISTRY = {
    "hermes": "evaluate.agents.hermes.call_agent",
    "claude_api": "evaluate.agents.claude_api.call_agent",
    "gemini_api": "evaluate.agents.gemini_api.call_agent",
}
```

### Step 5: Rewrite `evaluate/run.py` — model-aware dispatch

Current `select_agent()` returns a bare function. New version:

```python
import os
import time
from evaluate.model_registry import is_rate_limited, mark_rate_limited, select_model

AGENT_FALLBACK_CHAIN = ["claude_api", "gemini_api", "hermes"]

def _load_call_agent(agent_name: str):
    """Import and return call_agent function for the named agent."""
    import importlib
    module_path = AGENT_REGISTRY.get(agent_name)
    if not module_path:
        return None
    try:
        mod_path, func_name = module_path.rsplit(".", 1)
        mod = importlib.import_module(mod_path)
        return getattr(mod, func_name, None)
    except (ImportError, AttributeError):
        return None

def select_agent(agent_name: str | None = None) -> tuple[Callable, str, str]:
    """Return (call_agent_fn, effective_agent_name, effective_model).
    
    Picks the best available model for the configured agent.
    Falls back through AGENT_FALLBACK_CHAIN if primary agent is unavailable.
    """
    agent_name = agent_name or EVALUATION_AGENT
    fallback_chain = [agent_name] + [
        a for a in (EVALUATION_CONFIG.get("fallback_agents", []) or AGENT_FALLBACK_CHAIN)
        if a != agent_name
    ]
    
    for agent in fallback_chain:
        call_fn = _load_call_agent(agent)
        if not call_fn:
            continue
        
        model = select_model(agent)
        if model:
            return call_fn, agent, model
    
    raise RuntimeError(f"No available agent. Tried: {fallback_chain}")

def evaluate_one_job(job_data: dict, agent_name: str | None = None) -> dict | None:
    call_agent_fn, effective_agent, effective_model = select_agent(agent_name)
    
    prompt = build_prompt(job_data)
    raw_output = call_agent_fn(prompt)
    
    if raw_output is None:
        # Mark model as rate-limited and retry with next in chain
        mark_rate_limited(f"{effective_agent}/{effective_model}")
        return evaluate_one_job(job_data, agent_name)  # will pick next model
    
    result = extract_json(raw_output)
    if result:
        result["evaluated_by"] = f"{effective_agent}/{effective_model}"
    return result
```

### Step 6: Add `fallback_agents` to `haxjobs.toml`

```toml
[evaluation]
agent = "hermes"
fallback_agents = ["claude_api", "gemini_api"]
timeout_seconds = 180
```

Add `EVALUATION_FALLBACK_AGENTS` to `haxjobs_config.py`.

### Step 7: Add tests

Create `tests/test_evaluation_agents.py`:

```python
"""Tests for evaluation agent adapters — import-level only, no live calls."""

import pytest

def test_hermes_adapter_imports():
    from evaluate.agents.hermes import call_agent
    assert callable(call_agent)

def test_claude_api_adapter_imports():
    from evaluate.agents.claude_api import call_agent
    assert callable(call_agent)

def test_gemini_api_adapter_imports():
    from evaluate.agents.gemini_api import call_agent
    assert callable(call_agent)

def test_model_registry_imports():
    from evaluate.model_registry import (
        is_rate_limited, mark_rate_limited,
        get_hermes_models, select_model
    )
    assert callable(is_rate_limited)
    assert callable(get_hermes_models)

def test_model_registry_rate_limit_tracking():
    from evaluate.model_registry import is_rate_limited, mark_rate_limited
    mark_rate_limited("test/model")
    assert is_rate_limited("test/model")
    # ponytail: no cleanup — test-only state, ephemeral process

def test_agent_registry_has_expected_keys():
    from evaluate.agents import AGENT_REGISTRY
    assert "hermes" in AGENT_REGISTRY
    assert "claude_api" in AGENT_REGISTRY
    assert "gemini_api" in AGENT_REGISTRY

def test_select_agent_returns_callable():
    """Requires hermes to be configured."""
    from evaluate.run import _load_call_agent
    fn = _load_call_agent("hermes")
    assert callable(fn)
```

### Step 8: Update `.env.example`

Add any new API key env vars:
```
# Direct API fallbacks
ANTHROPIC_API_KEY=
GEMINI_API_KEY=
```

### Step 9: End-to-end verification

```bash
# All tests pass
PYTHONPATH=. python3 -m pytest -q

# Imports clean
PYTHONPATH=. python3 -m py_compile evaluate/model_registry.py evaluate/agents/hermes.py evaluate/agents/claude_api.py evaluate/agents/gemini_api.py evaluate/run.py

# Model registry works
PYTHONPATH=. python3 -c "from evaluate.model_registry import get_hermes_models; print(get_hermes_models())"

# Live evaluation (if models available)
PYTHONPATH=. python3 evaluate/run.py --next
```

## haxjobs.toml changes

```toml
[evaluation]
agent = "hermes"                              # Primary agent
fallback_agents = ["claude_api", "gemini_api"] # Auto-fallback chain
timeout_seconds = 180
```

## haxjobs_config.py changes

```python
EVALUATION_FALLBACK_AGENTS: list[str] = EVALUATION_CONFIG.get("fallback_agents", [])
```

## .env.example changes

```
# Direct API keys for evaluation fallback
ANTHROPIC_API_KEY=               # Claude API — reliable paid fallback
GEMINI_API_KEY=                  # Gemini API — free tier fallback
```

## Deliverables

- [ ] `evaluate/model_registry.py` — model/config reading + rate-limit tracking
- [ ] `evaluate/agents/hermes.py` — rewritten with native + external + model switching
- [ ] `evaluate/agents/claude_api.py` — new, stdlib HTTP adapter
- [ ] `evaluate/agents/gemini_api.py` — new, stdlib HTTP adapter
- [ ] `evaluate/agents/__init__.py` — updated with AGENT_REGISTRY
- [ ] `evaluate/run.py` — rewritten select_agent() with model awareness and fallback
- [ ] `haxjobs.toml` — added fallback_agents
- [ ] `haxjobs_config.py` — added EVALUATION_FALLBACK_AGENTS
- [ ] `.env.example` — added API key env vars
- [ ] `tests/test_evaluation_agents.py` — 7 tests
- [ ] All tests pass, py_compile clean

## STOP conditions

- If Hermes has NO importable Python API (Plan 027 found CLI-only), build only external mode with `--model` flag. Still wire model_registry.
- If no API keys are set (ANTHROPIC_API_KEY, GEMINI_API_KEY), skip those adapters. They're optional.
- If native import of hermes_cli causes dependency conflicts, fall back to external-only mode.
- Do NOT commit API keys.

## Done criteria

- [ ] `PYTHONPATH=. python3 -m pytest -q` — all tests pass
- [ ] `PYTHONPATH=. python3 -m py_compile` — clean across entire repo
- [ ] Changing `agent = "claude_api"` in haxjobs.toml switches evaluation to Claude API
- [ ] When Hermes GPT 5.5 is rate-limited, evaluation automatically uses DeepSeek (or falls back to Claude/Gemini API)
- [ ] `evaluate/run.py --next` works with at least 2 different agents/models
- [ ] Agent configs are read at runtime — adding a new model to Hermes config.yaml makes it immediately available
