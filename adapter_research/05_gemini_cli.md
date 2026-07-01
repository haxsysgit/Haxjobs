# Gemini CLI — HaxJobs Integration Research

**Date**: 2026-06-30  
**Version researched**: 0.41.2 (installed at `/usr/bin/gemini`)  
**Source**: Local CLI inspection (`gemini --help`, `~/.gemini/settings.json`)  
**GitHub**: [google-gemini/gemini-cli](https://github.com/google-gemini/gemini-cli) — TypeScript, Apache-2.0, last updated 2026-06-30T18:35:53Z  
**Language**: TypeScript (Node.js)  
**Researcher**: Pi Coding Agent

---

## Executive Summary

Gemini CLI (`gemini`) has first-class headless support: `-p/--prompt` for non-interactive mode, `-o/--output-format json` for JSON output, `-m/--model` for model selection, and `-y/--yolo` for auto-approvals. It also has the most mature extension/skills/hooks system among all agents. Integration is **subprocess-only** — no Python SDK.

Integration difficulty: ⭐⭐ EASY (subprocess, excellent automation flags)

---

## 1. Headless CLI Mode

### 1.1 Basic invocation

```bash
gemini -p "Evaluate this job..." -o json
```

### 1.2 Full automation flags

```bash
gemini \
  -p "Evaluate the candidate fit..." \
  -o json \
  -m "gemini-2.5-pro" \
  -y \                          # YOLO mode: auto-accept all actions
  --approval-mode yolo \        # Alternative: auto_edit, yolo, plan, default
  --skip-trust \                # Skip workspace trust dialog
  -s                            # Run in sandbox (optional)
```

### 1.3 JSON output

```bash
gemini -p "prompt" -o json
```

Output formats: `text` (default), `json`, `stream-json`.

### 1.4 Approval modes

| Flag | Effect |
|------|--------|
| `-y, --yolo` | Auto-accept ALL actions |
| `--approval-mode yolo` | Same as `-y` |
| `--approval-mode auto_edit` | Auto-approve edit tools only |
| `--approval-mode plan` | Read-only mode |
| `--approval-mode default` | Prompt for approval (default) |
| `--skip-trust` | Skip workspace trust dialog |

### 1.5 Authentication

Gemini CLI uses Google OAuth or API key:

```bash
# OAuth (interactive setup)
gemini login

# API key (for headless)
export GEMINI_API_KEY="..."
gemini -p "prompt" -o json
```

From `~/.gemini/`: `oauth_creds.json`, `google_accounts.json`, `settings.json`.

---

## 2. Config Files

### 2.1 Settings

**Location**: `~/.gemini/settings.json`

### 2.2 Google accounts

**Location**: `~/.gemini/google_accounts.json`  
Contains OAuth tokens for Google Cloud authentication.

### 2.3 Extensions & Skills

**Location**: `~/.gemini/extensions/` and `~/.gemini/skills/`

Gemini CLI has the most mature extension/skills system:
- `gemini extension install <name>` — install extensions
- `gemini skill install <name>` — install skills
- `-e, --extensions <names>` — enable specific extensions per session
- `-l, --list-extensions` — list available extensions

---

## 3. Model Discovery

Model selection via `-m/--model`:

```bash
gemini -p "prompt" -m "gemini-2.5-pro"
gemini -p "prompt" -m "gemini-2.5-flash"
```

Known Gemini models:
- `gemini-2.5-pro` — most capable
- `gemini-2.5-flash` — fast/cheap
- `gemini-3-flash-preview` — latest flash
- `gemini-3-pro` — latest pro
- `gemma-*` — local models (with `gemini gemma`)

---

## 4. Rate Limit Detection

```python
def _is_rate_limited(output: str) -> bool:
    markers = ["429", "rate limit", "quota exceeded", "RESOURCE_EXHAUSTED",
               "too many requests"]
    return any(m in output.lower() for m in markers)
```

### Model fallback chain

```python
models = ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-3-flash-preview"]
for model in models:
    result = subprocess.run([
        "gemini", "-p", prompt,
        "-o", "json",
        "-m", model,
        "-y", "--skip-trust",
    ], ...)
    if result.returncode == 0:
        return result.stdout
```

---

## 5. HaxJobs Adapter

```python
def call_agent(prompt: str, timeout_seconds: int = 300) -> str | None:
    models = ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-3-flash-preview"]
    
    for model in models:
        result = subprocess.run(
            [
                "gemini",
                "-p", prompt,
                "-o", "json",
                "-m", model,
                "-y",
                "--skip-trust",
            ],
            capture_output=True, text=True,
            timeout=timeout_seconds,
            cwd="/tmp",
            env={**os.environ, "GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY", "")}
        )
        
        if result.returncode == 0:
            try:
                return json.loads(result.stdout).get("result", result.stdout)
            except json.JSONDecodeError:
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
| Headless mode | ✅ `-p/--prompt` |
| JSON output | ✅ `-o json` |
| Structured schema | ❌ No `--json-schema` |
| Model selection | ✅ `-m/--model` |
| Approval bypass | ✅ `-y/--yolo`, `--approval-mode` |
| Read-only mode | ✅ `--approval-mode plan` |
| Extensions/Skills | ✅ ✅ Most mature system |
| API key auth | ✅ `GEMINI_API_KEY` |
| Native API | ❌ Subprocess only |
| Model fallback | ❌ No built-in fallback |

**Integration difficulty**: ⭐⭐ EASY — subprocess only, excellent automation flags.

---

## 7. Sources

| Source | Detail |
|--------|--------|
| `gemini --help` | Full CLI flag reference |
| `~/.gemini/settings.json` | User config (local) |
| `~/.gemini/google_accounts.json` | OAuth credentials (local) |
| GitHub | https://github.com/google-gemini/gemini-cli (Apache-2.0) |

*Research completed 2026-06-30. Source: direct CLI inspection.*
