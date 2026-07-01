# Claude Code — HaxJobs Integration Research

**Date**: 2026-06-30  
**Version researched**: 2.1.196 (installed at `~/.local/bin/claude`)  
**Source**: Local installation + [Claude Code Headless docs](https://code.claude.com/docs/en/headless) (fetched 2026-06-30) + [Agent SDK Python docs](https://code.claude.com/docs/en/agent-sdk/python) (fetched 2026-06-30) + [CLI Reference](https://code.claude.com/docs/en/cli-reference)  
**SDK**: `claude-agent-sdk` (pip-installable Python package), [GitHub](https://github.com/anthropics/claude-agent-sdk-python)  
**Language**: TypeScript (CLI) + Python SDK wrapper  
**Researcher**: Pi Coding Agent

---

## Executive Summary

Claude Code is the **second agent with a native Python API** (after Hermes). The `claude-agent-sdk` pip package provides `query()` and `ClaudeSDKClient` for programmatic access — no subprocess needed. It also supports **structured JSON Schema output** (like Codex) and **automatic model fallback** chains. This makes it the most feature-complete evaluation backend for HaxJobs.

Integration difficulty: ⭐ EASY (Python SDK + structured output + model fallback built-in)

---

## 1. Native Python SDK (In-Process)

### 1.1 Installation

```bash
pip install claude-agent-sdk
```

### 1.2 One-shot evaluation with `query()`

```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock

async def evaluate_job(prompt: str) -> dict:
    options = ClaudeAgentOptions(
        model="sonnet",                          # or "opus", "fable", full name
        fallback_model="fable",                  # auto-fallback on rate-limit
        permission_mode="bypassPermissions",     # headless: no prompts
        max_turns=1,                             # single turn for evaluation
        system_prompt=(
            "You are a job fit evaluator. "
            "Evaluate the candidate against the job description. "
            "Return ONLY valid JSON matching the schema."
        ),
        output_format={
            "type": "json_schema",
            "schema": {
                "type": "object",
                "properties": {
                    "fit_score": {"type": "integer", "minimum": 0, "maximum": 100},
                    "level": {"type": "integer", "minimum": 1, "maximum": 4},
                    "level_name": {"type": "string"},
                    "summary": {"type": "string"},
                    "gaps": {"type": "array", "items": {"type": "string"}},
                    "strengths": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["fit_score", "level", "level_name", "summary"],
                "additionalProperties": False,
            }
        },
        cwd="/tmp",                              # avoid loading project CLAUDE.md
        env={"ANTHROPIC_API_KEY": "sk-ant-..."}, # API key for cron
    )
    
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    import json
                    return json.loads(block.text)
    return None

# Run
result = asyncio.run(evaluate_job("Evaluate this job..."))
```

### 1.3 Persistent client with `ClaudeSDKClient`

For batched evaluation with model switching:

```python
async def evaluate_batch(jobs: list[str]) -> list[dict]:
    results = []
    
    async with ClaudeSDKClient(options=ClaudeAgentOptions(
        permission_mode="bypassPermissions",
        max_turns=1,
    )) as client:
        for i, job_prompt in enumerate(jobs):
            await client.query(job_prompt)
            
            async for message in client.receive_response():
                if isinstance(message, ResultMessage) and message.subtype == "success":
                    results.append(json.loads(message.result))
                elif isinstance(message, ResultMessage) and message.subtype == "error_during_execution":
                    # Rate limit — switch model
                    await client.set_model("fable")
                    await client.query(job_prompt)
                    # ... re-process
    
    return results
```

### 1.4 Key `ClaudeAgentOptions` fields

| Field | Type | Purpose |
|-------|------|---------|
| `model` | `str` | Model alias ('sonnet', 'opus', 'fable') or full name |
| `fallback_model` | `str` | Auto-switch on overload/rate-limit |
| `permission_mode` | `str` | `"bypassPermissions"` for headless |
| `max_turns` | `int` | Max tool-use round-trips (1 for pure eval) |
| `system_prompt` | `str` | Custom system instructions |
| `output_format` | `dict` | `{"type": "json_schema", "schema": {...}}` |
| `max_budget_usd` | `float` | Cost ceiling per query |
| `env` | `dict` | Environment overrides (API key, etc.) |
| `cwd` | `str` | Working directory |
| `allowed_tools` | `list[str]` | Auto-approved tools |
| `disallowed_tools` | `list[str]` | Blocked tools |

---

## 2. Headless CLI Mode (`claude -p`)

### 2.1 Basic invocation

```bash
claude -p "Evaluate this job..." --output-format json
```

### 2.2 Headless automation flags

```bash
claude -p "prompt" \
  --output-format json \
  --json-schema '{"type":"object","properties":{"score":{"type":"integer"}},"required":["score"]}' \
  --model sonnet \
  --fallback-model fable \
  --permission-mode bypassPermissions \
  --max-turns 1 \
  --bare \
  --settings '{"env":{"ANTHROPIC_API_KEY":"sk-ant-..."}}'
```

### 2.3 Key flags

| Flag | Purpose |
|------|---------|
| `-p, --print` | Non-interactive, print to stdout |
| `--output-format json` | JSON with session metadata |
| `--json-schema '<schema>'` | Structured output (inline JSON string) |
| `--model <alias>` | Model: sonnet, opus, fable, or full name |
| `--fallback-model <models>` | Comma-separated fallback chain |
| `--permission-mode bypassPermissions` | Skip all permission prompts |
| `--dangerously-skip-permissions` | Aggressive bypass (sandbox only) |
| `--max-turns <n>` | Limit tool-use rounds |
| `--bare` | Skip hooks, plugins, CLAUDE.md for clean CI runs |
| `--settings <file-or-json>` | Settings override |
| `--continue` | Continue last conversation |

### 2.4 JSON output format

```bash
claude -p "Summarize" --output-format json
```

Returns:
```json
{
  "result": "The project contains...",
  "session_id": "550e8400-...",
  "total_cost_usd": 0.042,
  "usage": {"input_tokens": 1200, "output_tokens": 300},
  "model": "claude-sonnet-4-5-20250929"
}
```

---

## 3. Model Discovery

### 3.1 Available model aliases

From CLI `--model` help and docs:

| Alias | Full Model | Use Case |
|-------|-----------|----------|
| `sonnet` | `claude-sonnet-4-5-20250929` | Fast, cheap — best for L1/L2 evaluation |
| `opus` | `claude-opus-4-5-20251101` | Most capable — use for L3 borderline cases |
| `fable` | `claude-fable-5` | Newest thinking model (2026) |

### 3.2 User's current settings

From `~/.claude/settings.json` (2026-06-30):

```json
{
  "model": "deepseek-v4-pro[1m]",
  "alwaysThinkingEnabled": true
}
```

User is using **DeepSeek V4 Pro** through Claude Code with 1M context. The `[1m]` suffix requests extended context window.

### 3.3 Reading model from HaxJobs

```python
import json

def get_claude_model():
    with open(os.path.expanduser("~/.claude/settings.json")) as f:
        settings = json.load(f)
    return settings.get("model", "sonnet")
```

### 3.4 Model fallback chain

Claude Code has **built-in fallback**: `--fallback-model sonnet,fable`. When the primary model returns an overload error, it automatically tries the fallback(s). For HaxJobs:

```python
ClaudeAgentOptions(
    model="sonnet",           # primary: fast & cheap
    fallback_model="fable",   # fallback 1: when sonnet overloaded
    # If both fail, HaxJobs falls back to next agent (Codex, Hermes)
)
```

---

## 4. Rate Limit Detection

### 4.1 SDK error handling

The SDK surfaces rate limits as `ResultMessage(subtype="error_during_execution")`:

```python
async for message in client.receive_response():
    if isinstance(message, ResultMessage):
        if message.subtype == "error_during_execution":
            error_text = message.errors[0] if message.errors else ""
            if "rate_limit" in error_text or "overloaded" in error_text:
                # Switch model or fall back to next agent
                return None
```

### 4.2 Streaming API retry events

When using `--output-format stream-json`, the CLI emits `system/api_retry` events with:
- `error`: category — `rate_limit`, `overloaded`, `server_error`, `billing_error`, `authentication_failed`
- `attempt` / `max_retries`: progress
- `retry_delay_ms`: wait time

### 4.3 Subprocess detection

```python
def _is_rate_limited(stderr: str) -> bool:
    markers = ["rate_limit", "overloaded", "529", "overloaded_error"]
    return any(m in stderr.lower() for m in markers)
```

---

## 5. Config & Settings

### 5.1 Settings file

**Location**: `~/.claude/settings.json`  
**Format**: JSON

```json
{
  "permissions": {
    "allow": ["mcp__pencil", "mcp__codegraph__codegraph_explore", ...]
  },
  "model": "deepseek-v4-pro[1m]",
  "alwaysThinkingEnabled": true,
  "enabledPlugins": {"ponytail@ponytail": true}
}
```

### 5.2 Config file

**Location**: `~/.claude/config.json`  
Contains: `primaryApiKey` (Anthropic API key)

### 5.3 OAuth credentials

**Location**: `~/.claude/.credentials.json`  
Contains: `claudeAiOauth.accessToken`, `refreshToken`, `expiresAt` for claude.ai managed auth

### 5.4 Auth priority (from docs)

In `--bare` mode:
1. `ANTHROPIC_API_KEY` env var
2. `apiKeyHelper` in `--settings` JSON
3. OAuth/keychain are NEVER read in bare mode

In normal mode:
1. `ANTHROPIC_API_KEY` env var
2. `apiKeyHelper`
3. OAuth from `~/.claude/.credentials.json`
4. Keychain

---

## 6. Integration Assessment

### 6.1 Recommended HaxJobs adapter: `evaluate/agents/claude.py`

```python
"""Claude Code evaluator — native Python SDK with structured output."""

import json, os, asyncio
from typing import Optional

async def _call_claude_sdk(prompt: str, timeout: int = 300) -> Optional[dict]:
    """Use Claude Agent SDK for in-process evaluation."""
    try:
        from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock
    except ImportError:
        return None  # SDK not installed, fall back to subprocess
    
    options = ClaudeAgentOptions(
        model="sonnet",
        fallback_model="fable",
        permission_mode="bypassPermissions",
        max_turns=1,
        system_prompt=(
            "You are a job fit evaluator. Evaluate the candidate against "
            "the job description. Return ONLY valid JSON."
        ),
        output_format={
            "type": "json_schema",
            "schema": _EVALUATION_SCHEMA,
        },
        cwd="/tmp",
    )
    
    try:
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if hasattr(block, 'text'):
                        return json.loads(block.text)
    except asyncio.TimeoutError:
        pass
    
    return None


def _call_claude_subprocess(prompt: str, timeout: int = 300) -> Optional[str]:
    """Fallback: subprocess when SDK not available."""
    import subprocess
    models = ["sonnet", "fable", "opus"]
    
    for model in models:
        result = subprocess.run(
            ["claude", "-p", prompt,
             "--output-format", "json",
             "--model", model,
             "--permission-mode", "bypassPermissions",
             "--max-turns", "1",
             "--bare"],
            capture_output=True, text=True, timeout=timeout,
            env={**os.environ, "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", "")}
        )
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                return data.get("result", result.stdout)
            except json.JSONDecodeError:
                if not _is_rate_limited(result.stderr):
                    return result.stdout
        # else: try next model
    
    return None


def call_agent(prompt: str, timeout_seconds: int = 300) -> Optional[str]:
    """Try SDK first, fall back to subprocess."""
    # Try native SDK
    try:
        result = asyncio.run(_call_claude_sdk(prompt, timeout_seconds))
        if result:
            return json.dumps(result)
    except Exception:
        pass
    
    # Fall back to subprocess
    return _call_claude_subprocess(prompt, timeout_seconds)


def _is_rate_limited(stderr: str) -> bool:
    markers = ["rate_limit", "overloaded", "529"]
    return any(m in stderr.lower() for m in markers)


_EVALUATION_SCHEMA = {
    "type": "object",
    "properties": {
        "fit_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "level": {"type": "integer", "minimum": 1, "maximum": 4},
        "level_name": {"type": "string"},
        "role_family": {"type": "string"},
        "tech_stack_match": {"type": "integer", "minimum": 0, "maximum": 30},
        "role_fit": {"type": "integer", "minimum": 0, "maximum": 35},
        "level_match": {"type": "integer", "minimum": 0, "maximum": 15},
        "location_match": {"type": "integer", "minimum": 0, "maximum": 10},
        "company_fit": {"type": "integer", "minimum": 0, "maximum": 10},
        "summary": {"type": "string"},
        "gaps": {"type": "array", "items": {"type": "string"}},
        "strengths": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["fit_score", "level", "level_name", "summary", "gaps", "strengths"],
    "additionalProperties": False,
}
```

### 6.2 Key advantages

| Feature | Claude Code | Codex | Hermes |
|---------|------------|-------|--------|
| Native Python API | ✅ `claude-agent-sdk` | ❌ | ✅ `agent.oneshot` |
| Structured JSON Schema | ✅ | ✅ `--output-schema` | ❌ |
| Auto model fallback | ✅ `--fallback-model` | ❌ | ✅ provider chain |
| Multiple models | ✅ sonnet/opus/fable | ❌ (OpenAI only) | ✅ 30+ providers |
| API key auth | ✅ `ANTHROPIC_API_KEY` | ✅ `CODEX_API_KEY` | ✅ config.yaml |
| Ephemeral mode | ✅ (`--bare` skips all) | ✅ `--ephemeral` | ✅ (`-z` always ephemeral) |

### 6.3 Shipping to Claude Code users

Claude Code has a **plugin system** (`--plugin-dir`, marketplace). HaxJobs could ship as a Claude Code plugin:

1. `.claude-plugin/plugin.json` manifest
2. Register skills for `/haxjobs:*` commands
3. Hook into `claude -p` for automated evaluation

But plugin is optional — the SDK adapter handles evaluation regardless.

---

## 7. Integration Difficulty: ⭐ EASY

- ✅ **Python SDK** — native in-process, no subprocess
- ✅ **Structured JSON Schema output** — validated, deterministic
- ✅ **Auto fallback model** — built into SDK
- ✅ **Multiple models** — sonnet (cheap), fable (new), opus (capable)
- ✅ **`--bare` mode** — clean CI/cron runs
- ✅ **Cost tracking** — `total_cost_usd` in JSON output
- ⚠️ Async-only SDK — requires `asyncio.run()` wrapper for sync callers
- ⚠️ SDK is a wrapper around the CLI binary — still needs `claude` installed

---

## 8. Sources & References

| Source | URL | Date |
|--------|-----|------|
| Claude Code Headless docs | https://code.claude.com/docs/en/headless | 2026-06-30 (fetched) |
| Agent SDK Python docs | https://code.claude.com/docs/en/agent-sdk/python | 2026-06-30 (fetched) |
| Agent SDK Structured Outputs | https://code.claude.com/docs/en/agent-sdk/structured-outputs | 2026-06-30 |
| Agent SDK GitHub | https://github.com/anthropics/claude-agent-sdk-python | 2026-06-30 |
| PyPI | https://pypi.org/project/claude-agent-sdk/ | 2026-06-30 |
| CLI Reference | https://code.claude.com/docs/en/cli-reference | 2026-06-30 |
| Settings file | `~/.claude/settings.json` (local) | 2026-06-30 |
| Config file | `~/.claude/config.json` (local) | 2026-06-30 |

---

*Research completed 2026-06-30. Source: direct CLI inspection (`claude --help`, `~/.claude/settings.json`, `~/.claude/config.json`), official docs at code.claude.com/docs, and the claude-agent-sdk Python package documentation.*
