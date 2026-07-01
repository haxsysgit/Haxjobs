# Plan 039: Bare-minimum native agent — core run loop, structured output

> **Executor instructions**: Follow this plan step by step. When done, update `plans/README.md`.
>
> **Drift check (run first)**: `ls src/haxjobs/agent/ 2>/dev/null`
> Plan 040 (package restructure) must be complete. If `src/haxjobs/` doesn't exist, STOP.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW (one file, no external deps beyond `openai` HTTP client)
- **Depends on**: 040, 042
- **Category**: direction
- **Planned at**: commit `cf70638`, 2026-06-30

## Why this matters

Plan 043 builds the full native agent (tool registry, built-in tools, context management). But plan 045 (onboarding) and plan 048 (evaluation) only need the core loop: send prompt → get response, optionally structured. This plan delivers just that — the minimum viable agent — so onboarding and evaluation can be built without waiting for the tool system.

Plan 043 later adds the tool layer on top of this foundation. Nothing in plan 039 gets deleted — it gets extended.

## What this plan delivers

`src/haxjobs/agent/agent.py` — ~40 lines:

```python
"""Minimal agent loop. Extended by plan 043 with tools + registry."""
import json
import os
import tomllib
from pathlib import Path
from openai import OpenAI


def _load_provider_config() -> dict:
    """Load provider config from ~/.haxjobs/config.toml or env vars."""
    config_path = Path.home() / ".haxjobs" / "config.toml"
    if config_path.exists():
        with open(config_path, "rb") as f:
            return tomllib.load(f)
    # Fallback: env vars for headless/cron use
    key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
    if key:
        base = os.getenv("HAXJOBS_API_BASE", "https://api.deepseek.com")
        model = os.getenv("HAXJOBS_MODEL", "deepseek-chat")
        return {"provider": {"api_key": key, "base_url": base, "model": model}}
    raise RuntimeError("No provider configured. Run haxjobs start and visit /setup.")


class Agent:
    """Thin wrapper over OpenAI-compatible chat API."""

    def __init__(self, model: str | None = None):
        cfg = _load_provider_config()
        p = cfg["provider"]
        self.client = OpenAI(api_key=p["api_key"], base_url=p["base_url"])
        self.model = model or p["model"]

    def run(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        """Single-turn: send prompt, return text response."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    def run_structured(
        self,
        prompt: str,
        system: str | None = None,
        json_schema: dict | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> dict:
        """Single-turn with structured JSON output."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_schema:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "response", "schema": json_schema},
            }
        response = self.client.chat.completions.create(**kwargs)
        return json.loads(response.choices[0].message.content)
```

## Steps

### Step 1: Add openai dependency

```bash
uv add openai
```

### Step 2: Create agent module

```bash
mkdir -p src/haxjobs/agent
```

Create `src/haxjobs/agent/__init__.py`:
```python
from haxjobs.agent.agent import Agent
__all__ = ["Agent"]
```

Create `src/haxjobs/agent/agent.py` as shown above.

### Step 3: Verify imports

```bash
uv run python -c "from haxjobs.agent import Agent; print('ok')"
```

### Step 4: Write tests

`tests/test_agent_minimal.py`:
- `test_agent_init` — loads config, creates client
- `test_agent_run` — mocks chat.completions.create, returns text
- `test_agent_run_structured` — mocks call, returns parsed dict
- `test_agent_no_config` — raises RuntimeError when no config

```bash
uv run pytest -q tests/test_agent_minimal.py
```

### Step 5: Commit

```bash
git commit -m "add bare-minimum native agent: single-turn run + structured output"
```

## Done criteria

- [ ] `Agent.run()` returns text from LLM
- [ ] `Agent.run_structured()` returns parsed dict from JSON schema
- [ ] Provider config loaded from `~/.haxjobs/config.toml`
- [ ] Falls back to `DEEPSEEK_API_KEY` env var
- [ ] 4 tests pass
- [ ] No tool registry, no multi-turn, no built-in tools — those are plan 043

## What plan 043 adds later

- `registry.py` — `ToolRegistry` with `@tool` decorator
- `tools.py` — `web_search`, `fetch_page` built-in tools
- Multi-turn agent loop with tool calling in `agent.py`
- Context window management (trimming old messages)
- `max_turns` parameter on `run()`

Nothing in this plan changes — 043 extends, doesn't replace.

## STOP conditions

- `from openai import OpenAI` fails → `uv add openai`
- `tomllib` not found → Python < 3.11? Check `python --version`. `tomllib` is stdlib in 3.11+.
