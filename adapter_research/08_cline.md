# Cline CLI — HaxJobs Integration Research

**Date**: 2026-06-30  
**Version researched**: 2.0 (CLI) — NOT installed on this system  
**Source**: [Cline CLI Reference](https://docs.cline.bot/cli/cli-reference) (fetched 2026-06-30) + [GitHub cline/cline](https://github.com/cline/cline) — TypeScript, Apache-2.0, 64K stars  
**Install**: `npm i -g @cline/cli`  
**Language**: TypeScript (Node.js)  
**Researcher**: Pi Coding Agent

---

## Executive Summary

Cline CLI has the **simplest headless invocation** of any agent: `cline "prompt"` — auto-approve is **enabled by default**. No `--yolo` or `--dangerously-skip-permissions` required. Supports `--json` for NDJSON output, `-m/--model` for model selection, `-P/--provider` for provider switching, `-k/--key` for API key override, and built-in **task scheduling** (`cline schedule`). Integration is subprocess-only.

Integration difficulty: ⭐ EASIEST (subprocess, zero permission flags needed)

---

## 1. Headless CLI Mode

### 1.1 Basic invocation (simplest of all agents)

```bash
cline "Evaluate this job..." --json
```

Auto-approve is **default true** — no permission bypass flag needed.

### 1.2 Full automation flags

```bash
cline "Evaluate the candidate fit..." \
  --json \
  --model "claude-sonnet-4-5" \
  --provider anthropic \
  --key "$ANTHROPIC_API_KEY" \
  --system "You are a job fit evaluator. Return ONLY valid JSON." \
  --timeout 300 \
  --cwd /tmp \
  --thinking low
```

### 1.3 Key flags

| Flag | Purpose |
|------|---------|
| `--json` | NDJSON output (one JSON per line) |
| `-m, --model <id>` | Model to use |
| `-P, --provider <id>` | Provider (cline, anthropic, openai, etc.) |
| `-k, --key <key>` | API key override |
| `-s, --system <prompt>` | System prompt override |
| `-p, --plan` | Plan mode (read-only, no edits) |
| `--auto-approve <bool>` | Already defaults to `true` |
| `-t, --timeout <seconds>` | Timeout (0 = none) |
| `--thinking <level>` | Reasoning effort: none/low/medium/high/xhigh |
| `-c, --cwd <path>` | Working directory |
| `--retries <count>` | Max consecutive mistakes before halt |

### 1.4 JSON output

```json
{"type": "say", "text": "The candidate scores 75/100...", "ts": 1760501486669, "say": "text"}
```

NDJSON format — parse all lines and concatenate `text` fields to get the full response.

### 1.5 Provider switching

```bash
cline "prompt" -P anthropic -m claude-sonnet-4-5 -k "$ANTHROPIC_API_KEY"
cline "prompt" -P openai -m gpt-5.5 -k "$OPENAI_API_KEY"
cline "prompt" -P cline -m cline-pro          # Cline's own provider
```

### 1.6 Built-in scheduling ⭐

Cline has the **only built-in scheduling system** of all agents:

```bash
cline schedule    # manage scheduled tasks
```

This could be relevant for HaxJobs cron integration.

---

## 2. Config

```
~/.cline/data/settings/providers.json   # API keys and provider config
~/.cline/data/settings/rules/           # Global rules
~/.cline/data/settings/skills/          # Global skills
~/.cline/data/sessions/                 # SQLite session DB
.cline/rules/                           # Project rules
.cline/skills/                          # Project skills
.cline/mcp.json                         # MCP server config
.cline/agents.yaml                      # Agent definitions
```

---

## 3. Model Discovery

```bash
cline config   # show current provider/model config
cline auth     # manage providers
```

---

## 4. Rate Limit Detection

```python
def _is_rate_limited(output: str) -> bool:
    markers = ["429", "rate limit", "too many requests", "quota exceeded"]
    return any(m in output.lower() for m in markers)
```

---

## 5. HaxJobs Adapter

```python
def call_agent(prompt: str, timeout_seconds: int = 300) -> str | None:
    result = subprocess.run(
        [
            "cline", prompt,
            "--json",
            "--timeout", str(timeout_seconds),
            "--cwd", "/tmp",
            "--thinking", "low",
        ],
        capture_output=True, text=True,
        timeout=timeout_seconds + 30,
    )
    
    if result.returncode == 0:
        # Parse NDJSON: extract all "text" fields
        texts = []
        for line in result.stdout.strip().split("\n"):
            try:
                obj = json.loads(line)
                if "text" in obj:
                    texts.append(obj["text"])
            except json.JSONDecodeError:
                pass
        return "\n".join(texts)
    
    return None
```

---

## 6. Integration Assessment

| Feature | Support |
|---------|---------|
| Headless mode | ✅ `cline "prompt"` (auto-approve default true) |
| JSON output | ✅ `--json` (NDJSON) |
| Structured schema | ❌ No `--json-schema` |
| Model selection | ✅ `-m/--model` |
| Provider switching | ✅ `-P/--provider` |
| API key override | ✅ `-k/--key` |
| System prompt | ✅ `-s/--system` |
| Approval bypass | ✅ Default true, zero flags needed |
| Plan mode | ✅ `-p/--plan` |
| Timeout | ✅ `-t/--timeout` |
| Retry limit | ✅ `--retries` |
| Task scheduling | ✅ `cline schedule` ⭐ unique |
| Native API | ❌ Subprocess only |

**Integration difficulty**: ⭐ EASIEST of all agents — zero permission flags needed, auto-approve is default, clean `cline "prompt" --json` is a valid automation call.

---

## 7. Sources

| Source | Detail |
|--------|--------|
| CLI Reference | https://docs.cline.bot/cli/cli-reference (fetched 2026-06-30) |
| GitHub | https://github.com/cline/cline (Apache-2.0, 64K stars) |
| CLI man page | https://github.com/cline/cline/blob/main/cli/man/cline.1.md |
| Blog (CLI 2.0) | https://cline.bot/blog/introducing-cline-cli-2-0 |

*Research completed 2026-06-30. Source: official docs + GitHub repo (not installed locally).*
