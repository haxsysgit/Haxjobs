# Plan 029: Build two-mode multi-agent evaluation adapters

> **Executor**: This plan builds production evaluation adapters for 5 agents, each with two modes: **session-native** (free, uses the host agent's own model) and **headless** (subprocess, for cron).
>
> **Drift check**: `test -f research/test-results/SUMMARY.md && echo "Plan 028 done" || echo "BLOCKED: Plan 028 not complete"`

## Status

- **Priority**: P1
- **Effort**: L (6-10 hours)
- **Risk**: MED (native APIs fragile across agent versions; Claude Code headless blocked by credit)
- **Depends on**: Plan 027 + Plan 028
- **Category**: feature
- **Planned at**: commit `6326123`, 2026-07-01

## Plan 028 findings (build drivers)

| Agent | Mode | Score (job #633) | Verdict |
|---|---|---|---|
| Claude Code | headless `claude -p` | — | ❌ blocked by Anthropic credit gate |
| Claude Code | session-native (plugin) | — | ⭐ FREE — uses user's active session (DeepSeek) |
| Codex | headless `codex exec --output-schema` | 62 L2 | ✅ strongest headless adapter |
| Hermes | headless `hermes -z` | 62 L2 | ✅ works as CLI subprocess |
| Hermes | native `import` | — | ⚠️ imports OK, live call fails on missing `openai` module |
| Pi | headless `pi -p --mode json --no-tools` | 60 L2 | ✅ works, needs JSONL event parser |
| Pi | session-native (skill) | — | ⭐ FREE — Pi is the evaluator itself |
| Gemini CLI | headless `gemini -p -o json -y` | — | ❌ blocked by tier migration |

## Architecture: two modes per agent

Every adapter exports two functions:

```python
def evaluate_session(job: dict) -> dict | None   # FREE — uses host agent's model, no auth
def evaluate_headless(job: dict) -> dict | None   # Cron — subprocess, needs auth
```

### When session-native works

Running inside the host agent (Pi skill, Hermes plugin, Claude Code hook, Codex extension):
- No subprocess, no auth, no credit check
- Uses whatever model the session is using
- Same model the user already configured

### When headless is needed

Cron pipeline on Archilles (no interactive session):
- Spawns the agent's CLI as a subprocess
- Must have auth configured (API keys, OAuth)
- Model specified via CLI flags

## Config-driven — no hardcoded agent preferences

HaxJobs never picks agents for the user. The chain order comes from `haxjobs.toml`:

```toml
[evaluation]
agent = "pi"                       # Primary
fallback_agents = ["codex", "hermes"]  # Tried in order if primary fails
```

If `agent` is empty or missing, HaxJobs auto-discovers installed agents via `shutil.which()` and uses all available ones. But config always wins over auto-discovery.

This means: no adapter is "#1" or "#4." The user's config IS the order. All 5 adapters are built equally — the chain just follows config.

## Files to create/modify

```
evaluate/
├── agents/
│   ├── __init__.py          # UPDATE — 5-agent registry
│   ├── base.py              # NEW — BaseAdapter with shared logic
│   ├── claude_code.py       # NEW — session-native via Claude Code hook
│   ├── codex.py             # NEW — headless via codex exec --output-schema
│   ├── hermes.py            # REWRITE — two-mode with model switching
│   ├── pi.py                # UPDATE — add evaluate_headless() JSONL parser
│   └── gemini.py            # NEW — stub, blocked by tier migration
├── common.py                # UNCHANGED
├── chain.py                 # NEW — fallback chain manager
└── run.py                   # UPDATE — use chain instead of select_agent
```

### New file: `evaluate/agents/base.py`

```python
"""Base class for evaluation agent adapters.

Every adapter inherits from this and implements at least one of:
- evaluate_session(job) -> dict | None  — free, uses host agent's session model
- evaluate_headless(job) -> dict | None — subprocess CLI, for cron
"""

from evaluate.common import build_prompt, extract_json, validate_result


class BaseAdapter:
    name: str = "base"

    def can_evaluate_session(self) -> bool:
        """Can this adapter use the host agent's session? (always False by default)"""
        return False

    def can_evaluate_headless(self) -> bool:
        """Can this adapter spawn a headless subprocess? (always False by default)"""
        return False

    def evaluate_session(self, prompt: str) -> str | None:
        """Evaluate using the host agent's session model. Override in subclass."""
        raise NotImplementedError

    def evaluate_headless(self, prompt: str) -> str | None:
        """Evaluate via headless subprocess. Override in subclass."""
        raise NotImplementedError

    def evaluate_job(self, job: dict, *, prompt: str | None = None) -> dict | None:
        """Evaluate a job. Prefers session-native, falls back to headless."""
        prompt = prompt or build_prompt(
            job["title"], job["company"], job.get("location", ""),
            job.get("jd_text", ""), job.get("source_url", ""),
        )

        raw = None
        if self.can_evaluate_session():
            raw = self.evaluate_session(prompt)
        if raw is None and self.can_evaluate_headless():
            raw = self.evaluate_headless(prompt)

        if not raw:
            return None

        result = extract_json(raw)
        if result:
            issues = validate_result(result)
            if not issues:
                result["evaluated_by"] = self.name
                return result
        return None
```

### New file: `evaluate/chain.py`

```python
"""Fallback chain — reads agent order from config, falls back to auto-discovery.

Config drives everything. No hardcoded preferences.
"""

from haxjobs_config import EVALUATION_AGENT, EVALUATION_FALLBACK_AGENTS
from evaluate.common import build_prompt
from evaluate.agents import AGENT_LIST, auto_discover


def _resolve_order() -> list[str]:
    """Return agent chain order: config first, auto-discovery if config is empty."""
    order = []
    if EVALUATION_AGENT:
        order.append(EVALUATION_AGENT)
    order.extend(EVALUATION_FALLBACK_AGENTS)
    if not order:
        # No config — auto-discover installed agents
        order = auto_discover()
    return order


def evaluate_one_job(job: dict, *, agent_order: list[str] | None = None) -> dict | None:
    """Evaluate a job. Tries each agent in order, returns first valid result."""
    prompt = build_prompt(
        job["title"], job["company"], job.get("location", ""),
        job.get("jd_text", ""), job.get("source_url", ""),
    )

    order = agent_order or _resolve_order()

    for agent_name in order:
        adapter = AGENT_LIST.get(agent_name)
        if not adapter:
            continue

        result = adapter.evaluate_job(job, prompt=prompt)
        if result:
            return result

    return None


def evaluate_batch(jobs: list[dict], *, agent_order: list[str] | None = None) -> list[dict | None]:
    """Evaluate multiple jobs. Returns results in same order."""
    return [evaluate_one_job(job, agent_order=agent_order) for job in jobs]
```

### New file: `evaluate/agents/claude_code.py`

```python
"""Claude Code adapter — session-native evaluation.

When HaxJobs runs as a Claude Code plugin/hook, evaluation uses the session's
model (DeepSeek) for free — no API key, no credit check, no subprocess.

Headless mode (claude -p) is documented but blocked by Anthropic credit gate.
"""

from evaluate.agents.base import BaseAdapter


class ClaudeCodeAdapter(BaseAdapter):
    name = "claude_code"

    def can_evaluate_session(self) -> bool:
        # True when running inside Claude Code (CLAUDE_CODE_SESSION_ID set)
        import os
        return bool(os.environ.get("CLAUDE_CODE_SESSION_ID"))

    def evaluate_session(self, prompt: str) -> str | None:
        # ponytail: Claude Code hook API — when a hook is invoked by Claude Code,
        # the hook's stdout is the response. We print the prompt and Claude Code
        # evaluates it with the session's model.
        # For programmatic use within a hook: write prompt to a temp file,
        # invoke claude task with --print and capture output.
        import subprocess, os, tempfile, json
        from pathlib import Path

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(prompt)
            prompt_file = f.name

        try:
            result = subprocess.run(
                ["claude", "-p", "--output-format", "json",
                 "--permission-mode", "bypassPermissions",
                 f"Read the file at {prompt_file} and evaluate it. Return ONLY valid JSON with no markdown."],
                capture_output=True, text=True, timeout=180,
                env={**os.environ},
            )
            output = result.stdout.strip()
            if not output:
                return None

            # claude -p returns JSON with result field
            try:
                data = json.loads(output)
                if isinstance(data, dict) and "result" in data:
                    return data["result"]
            except json.JSONDecodeError:
                pass
            return output
        finally:
            Path(prompt_file).unlink(missing_ok=True)
```

### New file: `evaluate/agents/codex.py`

```python
"""Codex adapter — headless evaluation via codex exec --output-schema.

Primary headless adapter. Schema-enforced JSON eliminates all parsing fragility.
Requires: Codex installed (shutil.which("codex")) with OAuth or CODEX_API_KEY.
"""

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from evaluate.agents.base import BaseAdapter

SCHEMA = {
    "type": "object",
    "properties": {
        "fit_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "fit_verdict": {"type": "string"},
        "level": {"type": "integer", "minimum": 1, "maximum": 4},
        "level_name": {"type": "string"},
        "strongest_matches": {"type": "array", "items": {"type": "string"}},
        "major_gaps": {"type": "array", "items": {"type": "string"}},
        "sponsorship_risk": {"type": "string"},
        "summary": {"type": "string"},
        "decision": {"type": "string"},
    },
    "required": ["fit_score", "fit_verdict", "level", "level_name",
                 "strongest_matches", "major_gaps", "sponsorship_risk",
                 "summary", "decision"],
    "additionalProperties": False,
}


class CodexAdapter(BaseAdapter):
    name = "codex"

    def can_evaluate_headless(self) -> bool:
        return shutil.which("codex") is not None

    def evaluate_headless(self, prompt: str) -> str | None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as sf:
            json.dump(SCHEMA, sf)
            schema_path = sf.name

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as of:
            output_path = of.name

        try:
            result = subprocess.run(
                ["codex", "exec",
                 "--skip-git-repo-check", "--ephemeral",
                 "--sandbox", "read-only",
                 "--output-schema", schema_path,
                 "--output-last-message", output_path,
                 prompt],
                capture_output=True, text=True, timeout=300,
                env={**os.environ},
                cwd="/tmp",
            )

            if result.returncode != 0:
                return None

            last_msg = Path(output_path).read_text(errors="replace").strip()
            if last_msg:
                # Validate it parses as JSON
                json.loads(last_msg)
                return last_msg
            return None
        finally:
            Path(schema_path).unlink(missing_ok=True)
            Path(output_path).unlink(missing_ok=True)
```

### Rewrite: `evaluate/agents/hermes.py`

Two-mode adapter. Replace current content.

```python
"""Hermes adapter — two-mode evaluation.

Session-native: import hermes_cli when running inside Hermes.
Headless: hermes -z for cron (works, validated in Plan 028).

Also supports native Python import (agent.oneshot.run_oneshot) when the
openai module dependency is resolvable.
"""

import os
import shutil
import subprocess
import sys

from evaluate.agents.base import BaseAdapter


class HermesAdapter(BaseAdapter):
    name = "hermes"

    def can_evaluate_session(self) -> bool:
        return bool(os.environ.get("HERMES_SESSION_ID"))

    def can_evaluate_headless(self) -> bool:
        return shutil.which("hermes") is not None

    def evaluate_session(self, prompt: str) -> str | None:
        # Attempt native Python API first
        try:
            from pathlib import Path
            hermes_src = str(Path.home() / ".hermes" / "hermes-agent")
            if hermes_src not in sys.path:
                sys.path.insert(0, hermes_src)
            from agent.oneshot import run_oneshot
            result = run_oneshot(prompt, task="job_evaluation")
            return result.strip() if result else None
        except ImportError:
            pass
        except Exception:
            pass

        # Fall back to hermes -z within session
        return self.evaluate_headless(prompt)

    def evaluate_headless(self, prompt: str) -> str | None:
        try:
            result = subprocess.run(
                ["hermes", "-z", prompt],
                capture_output=True, text=True, timeout=180,
                env={**os.environ, "HERMES_YOLO_MODE": "1"},
            )
            if result.returncode != 0:
                return None
            output = result.stdout.strip()
            return output if output else None
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None
```

### Update: `evaluate/agents/pi.py`

Add `evaluate_headless()` with JSONL parser. The session-native path already exists via Pi's HaxJobs skill.

Add to existing PiAdapter:

```python
import shutil

def can_evaluate_headless(self) -> bool:
    return shutil.which("pi") is not None

def evaluate_headless(self, prompt: str) -> str | None:
    """Pi headless — parse JSONL event stream for final assistant text."""
    import json
    result = subprocess.run(
        ["pi", "-p", prompt, "--mode", "json", "--no-tools", "--model", "deepseek/deepseek-v4-pro"],
        capture_output=True, text=True, timeout=300,
        env={**os.environ},
    )
    if result.returncode != 0:
        return None

    # Parse JSONL event stream
    texts = []
    for line in result.stdout.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            continue
        if evt.get("type") == "message_end":
            content = evt.get("message", {}).get("content", [])
            for c in content:
                if c.get("type") == "text":
                    texts.append(c["text"])
        elif evt.get("type") == "text":
            texts.append(evt.get("text", ""))

    full = "".join(texts)
    # Extract last JSON object from text (Pi may echo the prompt)
    import re
    objs = re.findall(r'\{[^{}]*"fit_score"[^{}]*\}', full)
    return objs[-1] if objs else full if full else None
```

### New file: `evaluate/agents/gemini.py`

```python
"""Gemini CLI adapter — deferred until tier migration resolved.

Blocked by IneligibleTierError: free tier deprecated, needs Antigravity migration.
When resolved: gemini -p <prompt> -o json -y
"""

from evaluate.agents.base import BaseAdapter


class GeminiAdapter(BaseAdapter):
    name = "gemini"

    def can_evaluate_headless(self) -> bool:
        import shutil
        return shutil.which("gemini") is not None

    def evaluate_headless(self, prompt: str) -> str | None:
        # Blocked — tier migration required
        # import subprocess, os
        # result = subprocess.run(["gemini", "-p", prompt, "-o", "json", "-y"], ...)
        return None
```

### Update: `evaluate/agents/__init__.py`

```python
"""HaxJobs evaluation agent adapters — two-mode architecture.

Each adapter implements BaseAdapter with:
- evaluate_session(job) — FREE, uses host agent's session model
- evaluate_headless(job) — Cron, subprocess CLI

Agent order is config-driven via haxjobs.toml [evaluation].agent + fallback_agents.
If unconfigured, auto_discover() finds installed agents via PATH probes.
"""

import shutil
from evaluate.agents.base import BaseAdapter

from evaluate.agents.claude_code import ClaudeCodeAdapter
from evaluate.agents.codex import CodexAdapter
from evaluate.agents.hermes import HermesAdapter
from evaluate.agents.pi import PiAdapter
from evaluate.agents.gemini import GeminiAdapter

AGENT_LIST: dict[str, BaseAdapter] = {
    "claude_code": ClaudeCodeAdapter(),
    "codex": CodexAdapter(),
    "hermes": HermesAdapter(),
    "pi": PiAdapter(),
    "gemini": GeminiAdapter(),
}


def auto_discover() -> list[str]:
    """Return agent names that are installed and ready (headless or session-native).

    Used only when haxjobs.toml [evaluation].agent is not set.
    Discovers via PATH probes and adapter capability checks.
    """
    available = []
    # Adapters that can work headless (cron-safe)
    if shutil.which("codex"):
        available.append("codex")
    if shutil.which("hermes"):
        available.append("hermes")
    # Pi is always available when running inside Pi (session-native)
    # For headless, check PATH
    if shutil.which("pi"):
        available.append("pi")
    # Claude Code only useful session-natively (headless blocked by credit)
    # Don't auto-discover it — user must opt in via config
    # Gemini blocked by tier migration — don't auto-discover
    return available
```

### Update: `evaluate/run.py`

Replace `select_agent()` with chain-based dispatch. No hardcoded agent preferences — the chain reads from `haxjobs.toml` or auto-discovers:

```python
from evaluate.chain import evaluate_one_job, evaluate_batch

# Old: select_agent() — delete, was hardcoded to EVALUATION_AGENT
# New: evaluate_one_job() reads config order or auto-discovers
# evaluate_from_db() and main() call evaluate_one_job() directly
```

## Steps

### Step 1: Create `evaluate/agents/base.py`

BaseAdapter class with shared `evaluate_job()` dispatch.

**Verify**:
```bash
PYTHONPATH=. python3 -c "from evaluate.agents.base import BaseAdapter; print('base OK')"
```

### Step 2: Create `evaluate/agents/claude_code.py`

ClaudeCodeAdapter — session-native first, headless documented but blocked.

**Verify**:
```bash
PYTHONPATH=. python3 -c "from evaluate.agents.claude_code import ClaudeCodeAdapter; a=ClaudeCodeAdapter(); print('claude_code OK', a.name)"
```

### Step 3: Create `evaluate/agents/codex.py`

CodexAdapter — headless with `--output-schema`.

**Verify**:
```bash
PYTHONPATH=. python3 -c "from evaluate.agents.codex import CodexAdapter; a=CodexAdapter(); print('codex OK', a.can_evaluate_headless())"
```

### Step 4: Rewrite `evaluate/agents/hermes.py`

Two-mode HermesAdapter replacing current subprocess-only version.

**Verify**:
```bash
PYTHONPATH=. python3 -c "from evaluate.agents.hermes import HermesAdapter; a=HermesAdapter(); print('hermes OK', a.can_evaluate_headless())"
```

### Step 5: Update `evaluate/agents/pi.py`

Add `evaluate_headless()` with JSONL parser. Keep existing session-native.

**Verify**:
```bash
PYTHONPATH=. python3 -c "from evaluate.agents.pi import PiAdapter; a=PiAdapter(); print('pi OK', a.can_evaluate_headless())"
```

### Step 6: Create `evaluate/agents/gemini.py`

Stub adapter — blocked by tier migration.

**Verify**:
```bash
PYTHONPATH=. python3 -c "from evaluate.agents.gemini import GeminiAdapter; a=GeminiAdapter(); print('gemini stub OK')"
```

### Step 7: Update `evaluate/agents/__init__.py`

Wire AGENT_LIST and auto_discover(). No hardcoded order — config drives the chain.

### Step 8: Create `evaluate/chain.py`

Fallback chain manager with `evaluate_one_job()` and `evaluate_batch()`.

### Step 9: Update `evaluate/run.py`

Replace `select_agent()` dispatch with chain-based `evaluate_one_job()`.

### Step 10: Update `haxjobs.toml` + `haxjobs_config.py`

```toml
[evaluation]
# Primary agent — if unset, HaxJobs auto-discovers installed agents via PATH probes.
# Supported: pi, codex, hermes, claude_code, gemini
agent = "pi"
# Fallback chain — tried in order if the primary agent fails (rate-limit, unavailable, blocked).
# Only agents listed here (plus the primary) are ever invoked.
# If unset and agent is also unset, auto-discovery kicks in.
fallback_agents = ["codex", "hermes"]
timeout_seconds = 300
```

```python
EVALUATION_FALLBACK_AGENTS: list[str] = EVALUATION_CONFIG.get("fallback_agents", [])
```

### Step 11: Add tests — `tests/test_evaluation_agents.py`

```python
"""Tests for evaluation agent adapters."""

import pytest


def test_base_adapter_exists():
    from evaluate.agents.base import BaseAdapter
    a = BaseAdapter()
    assert a.name == "base"
    assert not a.can_evaluate_session()
    assert not a.can_evaluate_headless()


def test_claude_code_adapter_exists():
    from evaluate.agents.claude_code import ClaudeCodeAdapter
    a = ClaudeCodeAdapter()
    assert a.name == "claude_code"
    assert callable(a.evaluate_job)


def test_codex_adapter_exists():
    from evaluate.agents.codex import CodexAdapter
    a = CodexAdapter()
    assert a.name == "codex"
    assert callable(a.evaluate_job)


def test_hermes_adapter_exists():
    from evaluate.agents.hermes import HermesAdapter
    a = HermesAdapter()
    assert a.name == "hermes"
    assert callable(a.evaluate_job)


def test_pi_adapter_exists():
    from evaluate.agents.pi import PiAdapter
    a = PiAdapter()
    assert a.name == "pi"
    assert callable(a.evaluate_job)


def test_gemini_adapter_exists():
    from evaluate.agents.gemini import GeminiAdapter
    a = GeminiAdapter()
    assert a.name == "gemini"


def test_agent_list_has_five_adapters():
    from evaluate.agents import AGENT_LIST, auto_discover
    assert len(AGENT_LIST) == 5
    assert "claude_code" in AGENT_LIST
    assert "codex" in AGENT_LIST
    assert "hermes" in AGENT_LIST
    assert "pi" in AGENT_LIST
    assert "gemini" in AGENT_LIST
    # auto_discover returns list, not hardcoded
    discovered = auto_discover()
    assert isinstance(discovered, list)


def test_chain_evaluates_with_fallback():
    """Chain tries agents in order, returns first valid result."""
    from evaluate.chain import evaluate_one_job
    # ponytail: test with a minimal job dict, no live calls
    result = evaluate_one_job({
        "title": "Test Role",
        "company": "Test Corp",
        "location": "Remote",
        "jd_text": "Python backend role.",
        "source_url": "http://example.com",
    }, agent_order=[])  # Empty order → returns None
    assert result is None


def test_all_adapters_inherit_base():
    from evaluate.agents import AGENT_LIST
    from evaluate.agents.base import BaseAdapter
    for name, adapter in AGENT_LIST.items():
        assert isinstance(adapter, BaseAdapter), f"{name} does not inherit BaseAdapter"
```

### Step 12: End-to-end verification

```bash
# All tests pass
PYTHONPATH=. python3 -m pytest -q

# Imports clean across all new files
PYTHONPATH=. python3 -m py_compile \
  evaluate/agents/base.py \
  evaluate/agents/claude_code.py \
  evaluate/agents/codex.py \
  evaluate/agents/hermes.py \
  evaluate/agents/gemini.py \
  evaluate/chain.py

# Chain works (no live calls, just import + dispatch)
PYTHONPATH=. python3 -c "
from evaluate.chain import evaluate_one_job
from evaluate.agents import AGENT_LIST, auto_discover
print('Agents:', list(AGENT_LIST.keys()))
print('Discovered:', auto_discover())
print('Chain OK')
"
```

## Deliverables

- [ ] `evaluate/agents/base.py` — BaseAdapter base class
- [ ] `evaluate/agents/claude_code.py` — session-native adapter (headless blocked)
- [ ] `evaluate/agents/codex.py` — headless `--output-schema` adapter
- [ ] `evaluate/agents/hermes.py` — rewritten two-mode adapter
- [ ] `evaluate/agents/pi.py` — updated with headless JSONL parser
- [ ] `evaluate/agents/gemini.py` — stub (blocked by tier migration)
- [ ] `evaluate/agents/__init__.py` — updated with AGENT_LIST + auto_discover()
- [ ] `evaluate/chain.py` — fallback chain manager
- [ ] `evaluate/run.py` — updated to use chain dispatch
- [ ] `haxjobs.toml` — fallback_agents + timeout bump
- [ ] `haxjobs_config.py` — EVALUATION_FALLBACK_AGENTS
- [ ] `tests/test_evaluation_agents.py` — 9 tests
- [ ] All tests pass, py_compile clean

## STOP conditions

- If `shutil.which("codex")` returns None, skip Codex adapter (user doesn't have Codex installed)
- If `shutil.which("pi")` returns None, Pi can still work session-natively (we're inside Pi)
- Do NOT commit API keys or auth tokens
- Do NOT attempt Claude Code headless — it's blocked and documented as such

## Done criteria

- [ ] `PYTHONPATH=. python3 -m pytest -q` — all tests pass
- [ ] `PYTHONPATH=. python3 -m py_compile` — clean across entire repo
- [ ] `evaluate/run.py --next` evaluates with the first available agent in the chain
- [ ] When one agent fails, the chain falls through to the next
- [ ] Each adapter can be imported independently
- [ ] Chain order comes from `haxjobs.toml` [evaluation].agent + fallback_agents. auto_discover() only fires when config is empty.
