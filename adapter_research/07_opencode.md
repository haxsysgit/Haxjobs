# Open Code — HaxJobs Integration Research

**Date**: 2026-06-30  
**Version researched**: 1.17.11 (installed at `/home/hax/.opencode/bin/opencode`)  
**Source**: Local CLI inspection (`opencode --help`, `opencode run --help`)  
**GitHub**: [anomalyco/opencode](https://github.com/anomalyco/opencode) — TypeScript, MIT, last updated 2026-06-30T18:38:08Z  
**Language**: TypeScript (Node.js)  
**Researcher**: Pi Coding Agent

---

## Executive Summary

Open Code (`opencode`) has a dedicated `opencode run [message]` command for headless execution, with `--format json` for JSON output, `--model provider/model` for model selection, `--dangerously-skip-permissions` for approval bypass, `--continue`/`--session` for session management, and a built-in server mode (`opencode serve`). Integration is **subprocess-only** — no Python SDK.

Integration difficulty: ⭐⭐ EASY (subprocess, clean automation flags)

---

## 1. Headless CLI Mode

### 1.1 Basic invocation

```bash
opencode run "Evaluate this job..." --format json
```

### 1.2 Full automation flags

```bash
opencode run "Evaluate the candidate fit..." \
  --format json \
  --model "anthropic/claude-sonnet-4-5" \
  --dangerously-skip-permissions \
  --dir /tmp
```

### 1.3 JSON output

```bash
opencode run "prompt" --format json
```

Output formats: `default` (formatted text) or `json` (raw JSON events).

### 1.4 Model selection

```bash
opencode run "prompt" --model "anthropic/claude-sonnet-4-5"
opencode run "prompt" --model "openai/gpt-5.5"
```

Format: `provider/model`. Use `opencode models` to list all available models per provider.

### 1.5 Model listing

```bash
opencode models                          # all models
opencode models anthropic                # filter by provider
opencode models --verbose                # include metadata/costs
opencode models --refresh                # refresh cache from models.dev
```

### 1.6 Approval bypass

```bash
opencode run "prompt" --dangerously-skip-permissions
```

Single flag: `--dangerously-skip-permissions` — auto-approves all permissions unless explicitly denied.

### 1.7 Session management

```bash
opencode run "follow-up" --continue                   # continue last session
opencode run "follow-up" --session <session-id>       # continue specific session
opencode run "follow-up" --fork --session <id>        # fork before continuing
```

### 1.8 Provider management

```bash
opencode providers list                    # list configured providers
opencode providers login [url]             # add provider
opencode providers logout [provider]       # remove provider
```

### 1.9 Server mode

```bash
opencode serve --port 4096                 # headless server mode
opencode attach http://localhost:4096      # connect to server
```

---

## 2. Agent system

Open Code has a built-in agent management system:

```bash
opencode agent create  # interactive agent creation
opencode agent list    # list all agents

# Use specific agent
opencode run "prompt" --agent "reviewer"
```

---

## 3. Model Discovery

```bash
# List all models (cached from models.dev)
opencode models

# Refresh cache
opencode models --refresh

# Verbose with metadata
opencode models --verbose

# Filter by provider
opencode models anthropic
```

---

## 4. Rate Limit Detection

```python
def _is_rate_limited(output: str) -> bool:
    markers = ["429", "rate limit", "too many requests", "quota exceeded",
               "overloaded"]
    return any(m in output.lower() for m in markers)
```

---

## 5. HaxJobs Adapter

```python
def call_agent(prompt: str, timeout_seconds: int = 300) -> str | None:
    models = [
        "anthropic/claude-sonnet-4-5",
        "openai/gpt-5.5",
        "google/gemini-2.5-pro",
    ]
    
    for model in models:
        result = subprocess.run(
            [
                "opencode", "run", prompt,
                "--format", "json",
                "--model", model,
                "--dangerously-skip-permissions",
                "--dir", "/tmp",
            ],
            capture_output=True, text=True,
            timeout=timeout_seconds,
        )
        
        if result.returncode == 0:
            return result.stdout
        
        if _is_rate_limited(result.stderr + result.stdout):
            continue
        break
    
    return None
```

---

## 6. Integration Assessment

| Feature | Support |
|---------|---------|
| Headless mode | ✅ `opencode run` |
| JSON output | ✅ `--format json` |
| Structured schema | ❌ No `--json-schema` |
| Model selection | ✅ `--model provider/model` |
| Model listing | ✅ `opencode models` |
| Provider mgmt | ✅ `opencode providers` |
| Approval bypass | ✅ `--dangerously-skip-permissions` |
| Server mode | ✅ `opencode serve` |
| Session mgmt | ✅ `--continue`, `--session`, `--fork` |
| Agent system | ✅ `opencode agent` |
| Native API | ❌ Subprocess only (but `serve` + `attach` available) |
| Model fallback | ❌ No built-in fallback |

**Integration difficulty**: ⭐⭐ EASY — subprocess only, clean automation flags.

---

## 7. Sources

| Source | Detail |
|--------|--------|
| `opencode --help` | Full CLI command reference |
| `opencode run --help` | Run command flags |
| `opencode models --help` | Model listing flags |
| `opencode providers --help` | Provider management |
| `opencode agent --help` | Agent management |
| GitHub | https://github.com/anomalyco/opencode (MIT) |

*Research completed 2026-06-30. Source: direct CLI inspection.*
