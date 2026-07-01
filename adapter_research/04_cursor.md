# Cursor Agent — HaxJobs Integration Research

**Date**: 2026-06-30  
**Version researched**: 3.8.11 (installed at `/usr/bin/cursor`)  
**Source**: Local CLI inspection (`cursor agent --help`, `~/.cursor/cli-config.json`)  
**GitHub**: Proprietary (Cursor IDE by Anysphere)  
**Language**: TypeScript/Electron (IDE-based agent CLI)  
**Researcher**: Pi Coding Agent

---

## Executive Summary

Cursor has a well-designed `cursor agent` CLI with explicit headless support via `-p/--print`, JSON output (`--output-format json`), model selection with parameter overrides, and approval bypass (`--force`/`--yolo`/`--trust`). It supports listing available models (`--list-models`), but requires authentication (API key or Cursor account). Integration is **subprocess-only** — no Python SDK.

Integration difficulty: ⭐⭐ EASY (subprocess only, but excellent automation flags)

---

## 1. Headless CLI Mode

### 1.1 Basic invocation

```bash
cursor agent -p "Evaluate this job..." --trust --output-format json
```

### 1.2 Full automation flags

```bash
cursor agent \
  -p "Evaluate the candidate fit..." \
  --output-format json \
  --model "gpt-5" \
  --force \                    # auto-approve commands unless explicitly denied
  --yolo \                     # alias for --force
  --trust \                    # trust workspace without prompting (only with --print)
  --mode plan \                # read-only mode (analyze, propose, no edits)
  --api-key "$CURSOR_API_KEY"
```

### 1.3 JSON output

```bash
cursor agent -p "prompt" --output-format json
```

Returns JSON (single result). Also supports `stream-json` for streaming.

### 1.4 Model selection

```bash
cursor agent -p "prompt" --model "gpt-5"
cursor agent -p "prompt" --model 'claude-opus-4-8[context=1m,effort=high,fast=false]'
```

Parameterized models support bracketed overrides:
- `context=1m` — extended context window
- `effort=high` — reasoning effort (low/medium/high/xhigh)
- `fast=false` — disable fast mode

### 1.5 Model listing

```bash
cursor agent --list-models   # requires authentication
```

### 1.6 Approval bypass

| Flag | Effect |
|------|--------|
| `-f, --force` | Run commands unless explicitly denied |
| `--yolo` | Alias for `--force` |
| `--trust` | Skip workspace trust dialog (only with `-p`) |
| `--mode plan` | Read-only: analyze, propose, no edits |
| `--mode ask` | Q&A style, read-only |

### 1.7 Authentication

```bash
# API key
CURSOR_API_KEY=sk-... cursor agent -p "prompt"

# Or via flag
cursor agent --api-key "sk-..." -p "prompt"

# Or login (interactive)
cursor agent login
```

---

## 2. Config Files

### 2.1 CLI config

**Location**: `~/.cursor/cli-config.json`

```json
{
  "permissions": {
    "allow": ["Shell(ls)"],
    "deny": []
  },
  "approvalMode": "allowlist",
  "sandbox": { "mode": "disabled" },
  "rewind": true
}
```

### 2.2 MCP config

**Location**: `~/.cursor/mcp.json`  
Contains MCP server definitions.

### 2.3 Agent configs

**Location**: `~/.cursor/agents/`  
Custom agent definitions.

---

## 3. Model Discovery

Models are server-side managed by Cursor. Use `--list-models` (requires auth) or check `~/.cursor/` for cached model lists. Known supported models include GPT-5 family, Claude Opus/Sonnet/Haiku, and Gemini models.

Parameterized model format: `'provider-model-version[param1=val1,param2=val2]'`

---

## 4. Rate Limit Detection

Cursor is a client for multiple providers. Rate limits surface as error text in stderr/stdout:

```python
def _is_rate_limited(output: str) -> bool:
    markers = ["rate limit", "429", "too many requests", "quota exceeded",
               "overloaded", "capacity"]
    return any(m in output.lower() for m in markers)
```

### Model fallback chain

```python
models = ["gpt-5", "claude-sonnet-4-5", "claude-opus-4-8"]
for model in models:
    result = subprocess.run([
        "cursor", "agent", "-p", prompt,
        "--output-format", "json",
        "--model", model,
        "--force", "--trust",
        "--mode", "plan",
    ], ...)
    if result.returncode == 0:
        return result.stdout
```

---

## 5. HaxJobs Adapter

```python
def call_agent(prompt: str, timeout_seconds: int = 300) -> str | None:
    models = ["gpt-5", "claude-sonnet-4-5", "claude-opus-4-8"]
    
    for model in models:
        result = subprocess.run(
            [
                "cursor", "agent",
                "-p", prompt,
                "--output-format", "json",
                "--model", model,
                "--force", "--trust",
                "--mode", "plan",
            ],
            capture_output=True, text=True,
            timeout=timeout_seconds,
            cwd="/tmp",
            env={**os.environ, "CURSOR_API_KEY": os.environ.get("CURSOR_API_KEY", "")}
        )
        
        if result.returncode == 0:
            try:
                return json.loads(result.stdout).get("result", result.stdout)
            except json.JSONDecodeError:
                return result.stdout
        
        if _is_rate_limited(result.stderr):
            continue  # try next model
        break  # non-rate-limit error, don't retry
    
    return None
```

---

## 6. Integration Assessment

| Feature | Support |
|---------|---------|
| Headless mode | ✅ `-p/--print` |
| JSON output | ✅ `--output-format json` |
| Structured schema | ❌ No `--json-schema` |
| Model selection | ✅ `--model`, parameterized overrides |
| Model listing | ✅ `--list-models` (needs auth) |
| Approval bypass | ✅ `--force`, `--yolo`, `--trust` |
| Read-only mode | ✅ `--mode plan` |
| API key auth | ✅ `--api-key` or `CURSOR_API_KEY` |
| Native API | ❌ Subprocess only |
| Model fallback | ❌ No built-in fallback |

**Integration difficulty**: ⭐⭐ EASY — subprocess only, but excellent automation flags.

---

## 7. Sources

| Source | Detail |
|--------|--------|
| `cursor agent --help` | Full CLI flag reference |
| `~/.cursor/cli-config.json` | User config (local, 2026-06-30) |
| Cursor 3.8.11 binary | `/usr/bin/cursor` |

*Research completed 2026-06-30. Source: direct CLI inspection.*
