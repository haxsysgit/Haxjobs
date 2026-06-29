# Plan 029: Build robust multi-agent evaluation stage

> **Executor**: This plan implements the evaluation adapters validated in Plan 028. It requires Plan 028's test results at `research/test-results/SUMMARY.md`. Only build adapters for agents marked "READY."
>
> **Drift check**: `test -f research/test-results/SUMMARY.md && cat research/test-results/SUMMARY.md | head -20` — confirms Plan 028 testing is done.

## Status

- **Priority**: P1
- **Effort**: L (building adapters is fast once the pattern is proven; 3-6 hours including testing)
- **Risk**: MED (depends on Plan 028 results; some agents may be flaky)
- **Depends on**: Plan 027 (research) + Plan 028 (testing)
- **Category**: feature
- **Planned at**: commit `421789b`, 2026-06-29

## Why this matters

After Plans 027-028, we know exactly which agents work and how to call them. Plan 029 builds the production adapters, wires them into `evaluate/run.py`'s `select_agent()`, and adds fallback chains so that if one agent is rate-limited, another takes over.

The goal is NOT to support every agent users might want — it's to build a small, tested set of adapters that work reliably, and make the pattern clear enough that adding a new one is a 30-line file.

## Architecture

```
evaluate/agents/
├── __init__.py              # Re-exports all call_agent functions
├── hermes.py                # Existing — subprocess: hermes chat
├── codex.py                 # NEW — subprocess: codex exec
├── claude_code.py           # NEW — subprocess: claude -p
├── gemini.py                # NEW — subprocess: gemini chat
├── claude_api.py            # NEW — HTTP: Anthropic Messages API
├── gemini_api.py            # NEW — HTTP: Google Generative Language API
└── pi.py                    # NEW — Pi skill approach (placeholder)
```

Each adapter exports ONE function:

```python
def call_agent(prompt: str, *, timeout_seconds: int = 180, retries: int = 2) -> str | None:
    """Send prompt to agent, return raw output text. Returns None on failure."""
```

### select_agent() changes

Current `select_agent()` in `evaluate/run.py`:
```python
def select_agent(agent_name: str | None = None) -> Callable:
    agent_name = agent_name or EVALUATION_AGENT
    if agent_name == "hermes":
        from evaluate.agents.hermes import call_agent
        return call_agent
    raise ValueError(f"Unknown agent: {agent_name}")
```

New `select_agent()` with fallback chain:
```python
AGENT_REGISTRY = {
    "hermes": "evaluate.agents.hermes",
    "codex": "evaluate.agents.codex",
    "claude": "evaluate.agents.claude_code",
    "gemini": "evaluate.agents.gemini",
    "claude_api": "evaluate.agents.claude_api",
    "gemini_api": "evaluate.agents.gemini_api",
    "pi": "evaluate.agents.pi",
}

AGENT_FALLBACK_CHAIN: list[str] = ["claude_api", "gemini_api", "hermes"]

def select_agent(agent_name: str | None = None) -> Callable:
    ...
```

The fallback chain means: if configured agent is "hermes" but hermes is rate-limited, try claude_api, then gemini_api. Configurable via `haxjobs.toml`:

```toml
[evaluation]
agent = "hermes"
fallback_agents = ["claude_api", "gemini_api"]
```

## Steps

### Step 1: Build adapters for READY agents

For each agent marked "READY" in Plan 028's SUMMARY.md, create `evaluate/agents/<agent>.py`.

Template (start from `evaluate/agents/hermes.py`):

```python
"""<Agent> adapter for HaxJobs evaluation."""

import os
import subprocess

BIN = "<binary>"
FLAGS = ["--flag1", "--flag2"]  # from Plan 028 test results

def call_agent(prompt: str, *, timeout_seconds: int = 180, retries: int = 2) -> str | None:
    for attempt in range(retries + 1):
        try:
            result = subprocess.run(
                [BIN, *FLAGS, prompt],
                capture_output=True, text=True, timeout=timeout_seconds,
                env={**os.environ, "HOME": os.path.expanduser("~")},
            )
            output = result.stdout.strip()
            if not output or "rate limit" in output.lower():
                continue
            return output
        except (subprocess.TimeoutExpired, Exception):
            continue
    return None
```

For HTTP-based adapters (claude_api, gemini_api), the template differs:

```python
"""Claude API adapter — direct Anthropic Messages API."""

import json
import os
import urllib.request

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-3-5-sonnet-20241022"

def call_agent(prompt: str, *, timeout_seconds: int = 180, retries: int = 2) -> str | None:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None

    payload = json.dumps({
        "model": MODEL,
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()

    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(API_URL, data=payload, headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            })
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                data = json.loads(resp.read())
                return data["content"][0]["text"]
        except Exception:
            continue
    return None
```

**Verify each**: 
```bash
PYTHONPATH=. python3 -c "
from evaluate.agents.codex import call_agent
result = call_agent('Return {\"ok\":true}', timeout_seconds=30)
print('OK' if result and 'ok' in result else 'FAIL')
"
```

### Step 2: Update select_agent() with registry + fallback

Update `evaluate/run.py`:

```python
AGENT_REGISTRY: dict[str, str] = {
    "hermes": "evaluate.agents.hermes",
    "codex": "evaluate.agents.codex",
    "claude": "evaluate.agents.claude_code",
    "gemini": "evaluate.agents.gemini",
    "claude_api": "evaluate.agents.claude_api",
    "gemini_api": "evaluate.agents.gemini_api",
}

def _load_agent(agent_name: str) -> Callable | None:
    """Import and return call_agent for the named agent. None if unavailable."""
    module_path = AGENT_REGISTRY.get(agent_name)
    if not module_path:
        return None
    try:
        import importlib
        mod = importlib.import_module(module_path)
        return getattr(mod, "call_agent", None)
    except (ImportError, AttributeError):
        return None

def select_agent(agent_name: str | None = None) -> Callable:
    agent_name = agent_name or EVALUATION_AGENT
    fallback_chain = EVALUATION_CONFIG.get("fallback_agents", [])
    
    call_agent_fn = _load_agent(agent_name)
    if call_agent_fn:
        return call_agent_fn
    
    # Try fallback chain
    for fb in fallback_chain:
        call_agent_fn = _load_agent(fb)
        if call_agent_fn:
            print(f"  (using fallback agent: {fb})")
            return call_agent_fn
    
    raise ValueError(f"No available agent. Configured: {agent_name}, fallbacks: {fallback_chain}")
```

### Step 3: Add fallback_agents to haxjobs.toml

```toml
[evaluation]
agent = "hermes"
fallback_agents = ["claude_api", "gemini_api"]
```

Add `EVALUATION_FALLBACK_AGENTS` constant to `haxjobs_config.py`.

### Step 4: Rate-limit awareness

Update `evaluate/run.py` `evaluate_one_job()` to detect rate limits and try fallbacks:

```python
def evaluate_one_job(job_data: dict, agent_name: str | None = None) -> dict | None:
    call_agent_fn = select_agent(agent_name)
    
    # ... build prompt ...
    
    raw_output = call_agent_fn(prompt, timeout_seconds=180)
    if raw_output is None:
        # Try fallback chain in select_agent
        ...
```

### Step 5: Basic test per adapter

For each new adapter, add a test in `tests/test_evaluation_agents.py`:

```python
def test_hermes_adapter_exists():
    from evaluate.agents.hermes import call_agent
    assert callable(call_agent)

def test_codex_adapter_exists():
    from evaluate.agents.codex import call_agent
    assert callable(call_agent)

# ... one per adapter
```

These are import-time tests only — no live agent calls in CI (agents may not be installed, may be rate-limited).

### Step 6: Final verification

```bash
# All tests pass
PYTHONPATH=. python3 -m pytest -q

# Each adapter imports cleanly
PYTHONPATH=. python3 -c "
from evaluate.agents.hermes import call_agent; print('hermes: OK')
from evaluate.agents.codex import call_agent; print('codex: OK')
from evaluate.agents.claude_api import call_agent; print('claude_api: OK')
"

# select_agent returns the right function
PYTHONPATH=. python3 -c "
from evaluate.run import select_agent
fn = select_agent('hermes')
assert fn.__module__ == 'evaluate.agents.hermes'
print('select_agent: OK')
"

# Live test with ONE agent (the one configured in haxjobs.toml)
PYTHONPATH=. python3 evaluate/run.py --next
```

## haxjobs.toml changes

```toml
[evaluation]
agent = "hermes"                         # Primary agent
fallback_agents = ["claude_api", "gemini_api"]  # Tried in order if primary fails
timeout_seconds = 180

[evaluation.levels]
auto_pack = [1, 2]
manual_review = [3]
skip = [4]
```

## haxjobs_config.py changes

```python
EVALUATION_FALLBACK_AGENTS: list[str] = EVALUATION_CONFIG.get("fallback_agents", [])
```

## Deliverables

- [ ] 3-6 new `evaluate/agents/<agent>.py` files (one per READY agent from Plan 028)
- [ ] Updated `evaluate/run.py` with `AGENT_REGISTRY`, `_load_agent()`, fallback logic
- [ ] Updated `haxjobs.toml` with `fallback_agents`
- [ ] Updated `haxjobs_config.py` with `EVALUATION_FALLBACK_AGENTS`
- [ ] `tests/test_evaluation_agents.py` with import-time tests per adapter
- [ ] `.env.example` updated with any new API key env vars
- [ ] `plans/README.md` updated

## STOP conditions

- If Plan 028 found ZERO agents other than Hermes, only build the registry/fallback infrastructure. The adapters can be added later when agents become available.
- If an adapter requires a dependency not in stdlib (`pip install anthropic`), use `urllib.request` (stdlib) instead. HaxJobs is stdlib-first.
- If `select_agent()` changes break existing evaluation flow — verify `evaluate/run.py --next` still works with hermes.

## Done criteria

- [ ] At least 2 evaluation agent adapters working (Hermes + at least 1 more, or Hermes + registry/framework if no others available)
- [ ] `select_agent()` supports registry lookup + fallback chain
- [ ] `PYTHONPATH=. python3 -m pytest -q` — all tests pass
- [ ] `PYTHONPATH=. python3 -m py_compile evaluate/run.py evaluate/agents/*.py` — clean
- [ ] A user can change `agent = "claude_api"` in haxjobs.toml and evaluation switches seamlessly
- [ ] If primary agent is rate-limited, fallback agent is used automatically
