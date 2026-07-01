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
| Config loading | Plan 044 (provider setup) | `haxjobs.features.setup.service.get_config()` from `~/.haxjobs/haxjobs.toml` |
| Single-turn `run()` | Hermes `oneshot.py:133-155` | Clean: system → user → call → return text |
| JSON parsing | `evaluate.common.extract_json()` | Already battle-tested: handles ``` fences, Hermes box chars, \\r\\n, brace-matching fallback |
| Template registry | Pi skills convention | Named prompts, reusable across evaluation/onboarding/wizard |

## Files

### `src/haxjobs/agent/agent.py` — ~65 lines

> **Reality notes**:
> - Config imports from `haxjobs.features.setup.service` (plan 044) — no duplicate TOML parsing.
> - `timeout=60` on the OpenAI client so API hangs don't stall the pipeline.
> - No `run_structured()`, no `json_schema`, no `_strip_code_fence`. Some providers don't
>   support `response_format`. Callers use `evaluate.common.extract_json()` on `run()` output
>   instead — it already handles ``` fences, Hermes box chars, `\r\n`, and brace-matching.
> - `~/.haxjobs/haxjobs.toml` is **provider credentials**. The repo's `haxjobs.toml` is
>   **product config** (roles, paths, cron). They are different files with the same name.

```python
"""Minimal agent loop — single-turn. Extended by plan 043 with tools + tiers."""
import os
from openai import OpenAI


class Agent:
    """Thin wrapper over OpenAI-compatible chat API."""

    def __init__(self, model: str | None = None, timeout: int = 60):
        cfg = self._load_config()
        p = cfg["provider"]
        self.client = OpenAI(
            api_key=p["api_key"], base_url=p["base_url"], timeout=timeout
        )
        self.model = model or p["model"]

    @staticmethod
    def _load_config() -> dict:
        """Load provider config from ~/.haxjobs/haxjobs.toml (provider credentials).

        NOT the repo haxjobs.toml (that's product config — roles, paths, cron).

        Primary: imports from haxjobs.features.setup.service (plan 044).
        Failsafe: env vars for headless/CI environments.
        """
        try:
            from haxjobs.features.setup.service import get_config
            cfg = get_config()
            if cfg:
                return cfg
        except ImportError:
            pass
        key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
        if key:
            base = os.getenv("HAXJOBS_API_BASE", "https://api.deepseek.com")
            model = os.getenv("HAXJOBS_MODEL", "deepseek-chat")
            return {"provider": {"api_key": key, "base_url": base, "model": model}}
        raise RuntimeError(
            "No provider configured. Run haxjobs start and visit /setup or "
            "set DEEPSEEK_API_KEY in your environment."
        )

    def run(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        """Single-turn: system → user → call → return text.
        
        Callers who need structured output should use evaluate.common.extract_json()
        on the returned text — it handles fences, box chars, and brace-matching.
        """
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
from haxjobs.agent.agent import Agent
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
- `test_agent_init` — loads config, creates client with timeout (mocked)
- `test_agent_run` — mocks chat.completions.create, returns raw text
- `test_agent_run_with_extract_json` — model returns ```json...``` → `extract_json()` from evaluate.common parses it
- `test_agent_no_config` — raises RuntimeError when no config
- `test_get_prompt_fills_variables` — {profile_json} gets filled
- `test_setup_service_integration` — `get_config()` from setup service returned correctly

```bash
uv run pytest -q tests/test_agent_minimal.py
```

### Step 5: Commit

```bash
git commit -m "add bare-minimum native agent: oneshot pattern + template registry + strip_fence"
```

## Done criteria

- [ ] `Agent.__init__()` creates OpenAI client with `timeout=60`
- [ ] `Agent.run()` returns raw text from LLM (system → user → call → return)
- [ ] JSON parsing delegated to `evaluate.common.extract_json()` (no `_strip_code_fence`, no `run_structured`)
- [ ] `get_prompt("evaluate_job", ...)` returns filled (system, user) tuple
- [ ] Provider config loaded from `~/.haxjobs/haxjobs.toml` via `haxjobs.features.setup.service.get_config()`
- [ ] Falls back to `DEEPSEEK_API_KEY` env var
- [ ] 6 tests pass
- [ ] No tool registry, no multi-turn, no prompt tiers — those are plan 043
- [ ] No `json_schema`/`response_format` — not all providers support it; `extract_json()` is more portable

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
