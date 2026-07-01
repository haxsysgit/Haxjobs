# GitHub Copilot CLI — HaxJobs Integration Research

**Date**: 2026-06-30  
**Version researched**: 1.0.43 (installed at `/usr/bin/copilot`)  
**Source**: Local CLI inspection (`copilot --help`)  
**GitHub**: `github/copilot-cli` or bundled with GitHub Copilot  
**Language**: TypeScript (Node.js)  
**Researcher**: Pi Coding Agent

---

## Executive Summary

GitHub Copilot CLI (`copilot`) has robust headless support: `-p/--prompt` for non-interactive mode, `--output-format json` for JSONL output, `--model` for model selection, `--yolo`/`--allow-all` for full auto-approval, `--silent` for clean scripting output, and `--share`/`--share-gist` for session export. Integration is **subprocess-only** — no Python SDK.

Integration difficulty: ⭐⭐ EASY (subprocess, excellent automation flags)

---

## 1. Headless CLI Mode

### 1.1 Basic invocation

```bash
copilot -p "Evaluate this job..." --allow-all-tools -s
```

### 1.2 Full automation flags

```bash
copilot \
  -p "Evaluate the candidate fit..." \
  --output-format json \
  --model "gpt-5.2" \
  --yolo \                          # enable all permissions
  --allow-all \                     # equivalent to --allow-all-tools --allow-all-paths --allow-all-urls
  -s \                              # silent mode: output only agent response (no stats)
  --effort medium \                 # reasoning effort: low/medium/high/xhigh
  --no-custom-instructions \        # skip AGENTS.md loading
  -C /tmp                           # change working directory
```

### 1.3 JSONL output

```bash
copilot -p "prompt" --output-format json -s
```

Output is **JSONL** (JSON Lines) — one JSON object per line. Use `-s` / `--silent` to suppress stats/status lines.

### 1.4 Approval/permission bypass

| Flag | Effect |
|------|--------|
| `--yolo` | Enable ALL permissions (tools + paths + URLs) |
| `--allow-all` | Same as `--yolo` |
| `--allow-all-tools` | Auto-approve all tools (required for non-interactive) |
| `--allow-all-paths` | Allow any file path |
| `--allow-all-urls` | Allow any URL |
| `--allow-tool=<tools>` | Allow specific tools |
| `--deny-tool=<tools>` | Deny specific tools |

### 1.5 Session export

```bash
copilot -p "prompt" --share              # exports session to ./copilot-session-<id>.md
copilot -p "prompt" --share-gist         # exports to secret GitHub Gist
copilot -p "prompt" --share /tmp/out.md  # custom path
```

### 1.6 Resume/continue

```bash
copilot -p "follow-up" --continue            # resume latest session
copilot -p "follow-up" --resume=<session-id> # resume specific session
copilot -p "follow-up" --resume="my feature" # resume by name
```

---

## 2. Config Files

Copilot CLI uses `~/.copilot/` directory:
- `~/.copilot/mcp-config.json` — MCP server configurations
- `~/.copilot/logs/` — log directory
- `~/.copilot/` — session storage

Custom instructions via `AGENTS.md` (can be skipped with `--no-custom-instructions`).

---

## 3. Model Discovery

Model selection via `--model`:

```bash
copilot -p "prompt" --model gpt-5.2
```

GitHub Copilot uses OpenAI models by default, with BYOK (Bring Your Own Key) support via `copilot providers`. Check available models:

```bash
# List available providers
copilot help providers

# Set custom provider
copilot providers --help
```

Env var for BYOK: `COPILOT_CUSTOM_PROVIDER_API_KEY`.

---

## 4. Rate Limit Detection

```python
def _is_rate_limited(output: str) -> bool:
    markers = ["429", "rate limit", "too many requests", "quota exceeded"]
    return any(m in output.lower() for m in markers)
```

Rate limits are tied to the GitHub Copilot subscription tier. For HaxJobs, switching models isn't easy since Copilot primarily uses GPT models.

---

## 5. HaxJobs Adapter

```python
def call_agent(prompt: str, timeout_seconds: int = 300) -> str | None:
    result = subprocess.run(
        [
            "copilot",
            "-p", prompt,
            "--output-format", "json",
            "-s",                      # silent: no stats
            "--yolo",                  # all permissions
            "--no-custom-instructions", # skip AGENTS.md
            "-C", "/tmp",
        ],
        capture_output=True, text=True,
        timeout=timeout_seconds,
    )
    
    if result.returncode == 0:
        # Parse JSONL: last line is the final message
        lines = [l for l in result.stdout.strip().split("\n") if l.strip()]
        if lines:
            import json
            try:
                last = json.loads(lines[-1])
                return last.get("text", last.get("content", lines[-1]))
            except json.JSONDecodeError:
                return lines[-1]
    
    return None
```

---

## 6. Integration Assessment

| Feature | Support |
|---------|---------|
| Headless mode | ✅ `-p/--prompt` |
| JSON output | ✅ `--output-format json` (JSONL) |
| Structured schema | ❌ No `--json-schema` |
| Model selection | ✅ `--model` |
| Approval bypass | ✅ `--yolo`, `--allow-all`, `--allow-all-tools` |
| Silent mode | ✅ `-s/--silent` |
| Session export | ✅ `--share`, `--share-gist` |
| Session resume | ✅ `--continue`, `--resume` |
| Reasoning effort | ✅ `--effort low/medium/high/xhigh` |
| BYOK | ✅ `COPILOT_CUSTOM_PROVIDER_API_KEY` |
| Native API | ❌ Subprocess only |
| Model fallback | ❌ No built-in fallback |

**Integration difficulty**: ⭐⭐ EASY — subprocess only, excellent automation flags.

---

## 7. Sources

| Source | Detail |
|--------|--------|
| `copilot --help` | Full CLI flag reference |
| `copilot help permissions` | Permission documentation |
| `copilot help providers` | Custom provider documentation |
| `/usr/bin/copilot` | Binary, v1.0.43 |

*Research completed 2026-06-30. Source: direct CLI inspection.*
