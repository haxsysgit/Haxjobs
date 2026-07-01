# Plan 039: Bare-minimum native agent — core run loop, structured output

> **Executor instructions**: Read all of `haxjobs_agent_lab/analysis.md` and `analysis-docs.md` first.
> These document the Hermes patterns (oneshot, strip_fence, template registry) and Pi patterns (factory dispatch, skill convention) that inform this implementation.
>
> **Drift check (run first)**: `ls src/haxjobs/agent/ 2>/dev/null`
> Plan 040 (package restructure) must be complete. If `src/haxjobs/` doesn't exist, STOP.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: 040, 044
- **Category**: direction
- **Planned at**: commit `07daac6`, 2026-06-30

## Why this matters

Plan 043 builds the full native agent (tool registry, prompt tiers, identity). But plan 045 (onboarding) and plan 048 (evaluation) only need single-turn: send prompt → get response. This plan delivers just that, copied from Hermes' `oneshot.py` pattern, so onboarding and evaluation can be built without waiting for the tool system.

Plan 043 extends everything here — nothing gets deleted.

## Design — copied from Hermes + Pi analysis

From `haxjobs_agent_lab/analysis.md` and analysis of Hermes' `agent/oneshot.py`:

| What | Source | Lines |
|------|--------|-------|
| Config loading | Plan 042 design | ~/.haxjobs/config.toml |
| Single-turn `run()` | Hermes `oneshot.py:133-155` | Clean: system → user → call → strip_fence → return |
| `run_structured()` | OpenAI `response_format` | JSON schema enforcement |
| `_strip_code_fence()` | Hermes `oneshot.py:163-170` | Models wrap JSON in ``` — strip exactly one layer |
| Template registry | Pi skills convention | Named prompts, reusable across evaluation/onboarding/wizard |

## Files

### `src/haxjobs/agent/agent.py` — ~70 lines

```python
"""Minimal agent loop — single-turn. Extended by plan 043 with tools + tiers."""
import json
import os
import re
import tomllib
from pathlib import Path
from openai import OpenAI


def _load_provider_config() -> dict:
    """Load provider config from ~/.haxjobs/config.toml or env vars."""
    config_path = Path.home() / ".haxjobs" / "config.toml"
    if config_path.exists():
        with open(config_path, "rb") as f:
            return tomllib.load(f)
    key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
    if key:
        base = os.getenv("HAXJOBS_API_BASE", "https://api.deepseek.com")
        model = os.getenv("HAXJOBS_MODEL", "deepseek-chat")
        return {"provider": {"api_key": key, "base_url": base, "model": model}}
    raise RuntimeError("No provider configured. Run haxjobs start and visit /setup.")


def _strip_code_fence(text: str) -> str:
    """Strip a single layer of ``` fences if present. Hermes pattern."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[^\n]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()


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
        """Single-turn: system → user → call → strip_fence → return text."""
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
        return _strip_code_fence(response.choices[0].message.content or "")

    def run_structured(
        self,
        prompt: str,
        system: str | None = None,
        json_schema: dict | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> dict:
        """Single-turn with structured JSON output. Strips fences."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        kwargs: dict = {
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
        text = _strip_code_fence(response.choices[0].message.content or "")
        return json.loads(text)
```

### `src/haxjobs/agent/prompts.py` — ~30 lines

Template registry for named prompts. Copied from the oneshot.py pattern.

```python
"""Named prompt templates. Reusable across evaluation, onboarding, wizard."""
from dataclasses import dataclass

@dataclass(frozen=True)
class PromptTemplate:
    system: str
    user: str  # template with {variables}


PROMPTS: dict[str, PromptTemplate] = {
    "evaluate_job": PromptTemplate(
        system="You are a job-candidate fit evaluator. Score from 0-100. Be honest.",
        user="Profile:\n{profile_json}\n\nJob:\n{job_json}\n\nEvaluate fit.",
    ),
    "extract_cv": PromptTemplate(
        system="Extract structured profile data from a CV. Return valid JSON only.",
        user="CV text:\n{cv_text}\n\nExtract: name, email, phone, skills, experience, education, projects.",
    ),
    "wizard_question": PromptTemplate(
        system="Generate one targeted question to refine a job search profile. Be specific — no generic questions.",
        user="Current profile:\n{profile_json}\n\nGap areas: {gaps}\n\nGenerate one question.",
    ),
}


def get_prompt(name: str, **variables) -> tuple[str, str]:
    """Return (system, user) with variables filled."""
    t = PROMPTS[name]
    return t.system, t.user.format(**variables)
```

### `src/haxjobs/agent/__init__.py` — 3 lines

```python
from haxjobs.agent.agent import Agent, _strip_code_fence
from haxjobs.agent.prompts import get_prompt, PromptTemplate, PROMPTS
__all__ = ["Agent", "get_prompt", "PromptTemplate", "PROMPTS"]
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

Write `__init__.py`, `agent.py`, and `prompts.py` as above.

### Step 3: Verify imports

```bash
uv run python -c "from haxjobs.agent import Agent, get_prompt; print('ok')"
```

### Step 4: Write tests

`tests/test_agent_minimal.py`:
- `test_agent_init` — loads config, creates client (mocked)
- `test_agent_run` — mocks chat.completions.create, returns stripped text
- `test_agent_run_stripped_fence` — model returns ```json...``` → Agent strips fences
- `test_agent_run_structured` — mocks call with JSON schema, returns parsed dict
- `test_agent_no_config` — raises RuntimeError when no config
- `test_get_prompt_fills_variables` — {profile_json} gets filled
- `test_strip_code_fence` — test _strip_code_fence directly with various fence formats

```bash
uv run pytest -q tests/test_agent_minimal.py
```

### Step 5: Commit

```bash
git commit -m "add bare-minimum native agent: oneshot pattern + template registry + strip_fence"
```

## Done criteria

- [ ] `Agent.run()` returns stripped text from LLM (Hermes oneshot pattern)
- [ ] `Agent.run_structured()` returns parsed dict (OpenAI JSON schema)
- [ ] `_strip_code_fence()` handles ```json, ```, and mixed fences
- [ ] `get_prompt("evaluate_job", ...)` returns filled (system, user) tuple
- [ ] Provider config loaded from `~/.haxjobs/config.toml`
- [ ] Falls back to `DEEPSEEK_API_KEY` env var
- [ ] 7 tests pass
- [ ] No tool registry, no multi-turn, no prompt tiers — those are plan 043

## What plan 043 adds later

- `registry.py` — AST auto-discovery of tools (copied from Hermes)
- `tools.py` — `web_search`, `fetch_page` with `check_fn` availability gating
- `prompt.py` — 3-tier system prompt: stable/context/volatile (copied from Hermes)
- `identity.py` — loads `~/.haxjobs/soul.md` (Hermes SOUL.md pattern)
- Multi-turn `run_with_tools()` on Agent class
- Agent-level tools (tools that bypass registry for DB access)
- Context trimming when approaching model limits

Nothing in this plan changes — 043 extends, doesn't delete.

## STOP conditions

- `from openai import OpenAI` fails → `uv add openai`
- `tomllib` not found → Python < 3.11? Check `python --version`
