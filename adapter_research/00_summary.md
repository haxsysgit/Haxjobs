# HaxJobs Agent Integration Research — Summary

**Date**: 2026-06-30  
**Plan**: 027 — Research coding agent internals, APIs, integration points, and model switching  
**Researcher**: Pi Coding Agent (Claude model) via direct source inspection + web research

---

## Quick Reference Table

| # | Agent | Version | Integration | Difficulty | Native API? | JSON Output | Structured Schema | Model Fallback |
|---|-------|---------|-------------|------------|-------------|-------------|-------------------|----------------|
| 1 | **Hermes** | 0.17.0 | Native Python + Subprocess | ⭐ TRIVIAL | ✅ `agent.oneshot` | ❌ plain text | ❌ | ✅ 7-provider chain |
| 2 | **Claude Code** | 2.1.196 | Python SDK + Subprocess | ⭐ EASY | ✅ `claude-agent-sdk` | ✅ `--output-format json` | ✅ `--json-schema '{}'` | ✅ `--fallback-model` |
| 3 | **Codex** | 0.139.0 | Subprocess only | ⭐⭐ EASY | ❌ | ✅ `--output-schema` | ✅ `--output-schema file.json` | ❌ |
| 4 | **Cursor** | 3.8.11 | Subprocess only | ⭐⭐ EASY | ❌ | ✅ `--output-format json` | ❌ | ❌ |
| 5 | **Gemini CLI** | 0.41.2 | Subprocess only | ⭐⭐ EASY | ❌ | ✅ `-o json` | ❌ | ❌ |
| 6 | **Copilot CLI** | 1.0.43 | Subprocess only | ⭐⭐ EASY | ❌ | ✅ `--output-format json` | ❌ | ❌ |
| 7 | **Open Code** | 1.17.11 | Subprocess only | ⭐⭐ EASY | ❌ | ✅ `--format json` | ❌ | ❌ |
| 8 | **Cline** | 2.0 (CLI) | Subprocess only | ⭐ EASIEST | ❌ | ✅ `--json` | ❌ | ❌ |

---

## Integration Tiers

### Tier 1: Native Python API (in-process)

**Hermes** — `from agent.oneshot import run_oneshot` — direct function call, zero subprocess overhead. Has automatic multi-provider fallback chain (7 providers) on rate limit/credit exhaustion.

**Claude Code** — `pip install claude-agent-sdk` + `from claude_agent_sdk import query, ClaudeAgentOptions` — async Python SDK. Supports structured JSON Schema output AND automatic model fallback (`fallback_model`).

### Tier 2: Subprocess with Structured Output

**Codex** — `codex exec --output-schema schema.json` — guarantees valid JSON output matching a provided schema. Best for deterministic evaluation pipelines. Limited to OpenAI models (gpt-5.5, gpt-5.4).

### Tier 3: Subprocess with JSON Output

**Cursor**, **Gemini CLI**, **Copilot CLI**, **Open Code** — all support `--output-format json` and `--model` selection. No structured schema validation, no built-in model fallback. Need explicit multi-model retry logic in the HaxJobs adapter.

### Tier 4: Simplest Automation

**Cline** — `cline "prompt" --json` — auto-approve is default true. No permission bypass flags needed. Cleanest subprocess invocation of all agents.

---

## Recommendation for HaxJobs Pipeline

### Primary evaluator chain (in order):

1. **Claude Code SDK** (native Python, structured output, model fallback) — if `claude-agent-sdk` installed
2. **Hermes** (native Python, provider fallback, already working) — always available
3. **Codex** (structured JSON via `--output-schema`) — for validated output guarantee
4. **Gemini CLI** (widely available, fast flash models) — cheap fallback
5. **Cursor**, **Open Code**, **Copilot CLI**, **Cline** — additional fallback options

### Implementation approach:

```python
# evaluate/run.py — agent fallback chain
_AGENT_FALLBACK_CHAIN = [
    "claude",    # native Python SDK + structured output
    "hermes",    # native Python API + provider fallback
    "pi",        # already implemented
    "codex",     # structured JSON via --output-schema
    "gemini",    # fast/cheap fallback
]
```

---

## Reports

Detailed per-agent reports in this directory:

| File | Agent | Depth |
|------|-------|-------|
| [01_hermes_agent.md](01_hermes_agent.md) | Hermes | Deep — full source trace, API signatures, provider chain |
| [02_codex.md](02_codex.md) | Codex CLI | Deep — official docs + CLI inspection, output schema |
| [03_claude_code.md](03_claude_code.md) | Claude Code | Deep — Python SDK full API, headless CLI, settings |
| [04_cursor.md](04_cursor.md) | Cursor Agent | Standard — CLI flags, config, adapter |
| [05_gemini_cli.md](05_gemini_cli.md) | Gemini CLI | Standard — CLI flags, extensions, adapter |
| [06_copilot_cli.md](06_copilot_cli.md) | Copilot CLI | Standard — CLI flags, permissions, adapter |
| [07_opencode.md](07_opencode.md) | Open Code | Standard — CLI flags, providers, adapter |
| [08_cline.md](08_cline.md) | Cline | Standard — official docs (not installed) |

---

## Key Architectural Insights

1. **Only 2 agents have native Python APIs**: Hermes and Claude Code. All others are subprocess-only.
2. **Only 2 agents have structured JSON Schema output**: Codex (`--output-schema`) and Claude Code (`--json-schema`).
3. **Hermes has the most sophisticated provider fallback**: 7-provider auto-detection chain with HTTP 402/429 handling.
4. **Claude Code has the best combined feature set**: native Python SDK + structured output + model fallback.
5. **Cline has the simplest automation**: auto-approve is default true, `cline "prompt" --json` is a complete headless call.
6. **No agent has a synchronous Python evaluation function** out of the box — Hermes' `run_oneshot` is close, Claude SDK is async-only. HaxJobs needs to wrap with `asyncio.run()` or subprocess.

---

*Research completed 2026-06-30. All line numbers, function signatures, and config paths verified against installed code or official documentation.*
