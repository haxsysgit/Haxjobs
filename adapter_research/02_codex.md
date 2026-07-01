# Codex CLI — HaxJobs Integration Research

**Date**: 2026-06-30  
**Version researched**: 0.139.0 (installed at `/usr/bin/codex`)  
**Source**: Local installation + [OpenAI Codex docs](https://developers.openai.com/codex/noninteractive) (fetched 2026-06-30) + [CLI Reference](https://developers.openai.com/codex/cli/reference)  
**GitHub**: [openai/codex](https://github.com/openai/codex) — Rust, Apache-2.0, last updated 2026-06-30T18:33:04Z  
**Language**: Rust (compiled binary, no importable Python/JS API)  
**Researcher**: Pi Coding Agent

---

## Executive Summary

Codex is a **subprocess-only** integration — compiled Rust binary with no importable library. Its `codex exec` non-interactive mode is purpose-built for CI/automation and supports **structured JSON output via `--output-schema`**, making it the most reliable evaluation backend for automated pipelines. The key win over other subprocess agents: Codex can be forced to return **validated JSON** matching a schema, eliminating the "parse arbitrary text into JSON" problem entirely.

Integration difficulty: ⭐⭐ EASY (subprocess only, but excellent automation support)

---

## 1. Non-Interactive Mode (`codex exec`)

### 1.1 Basic invocation

```bash
codex exec "summarize the repository structure"
```

- Streams progress to **stderr**
- Prints **final agent message only** to **stdout**
- Exit code 0 = success, non-zero = failure

### 1.2 Headless automation flags

```bash
codex exec \
  --ephemeral \                          # no session persistence to disk
  --skip-git-repo-check \                # run outside a git repo
  --sandbox workspace-write \            # allow file edits  
  --dangerously-bypass-approvals-and-sandbox \  # no user prompts (headless)
  --ignore-user-config \                 # skip ~/.codex/config.toml
  --ignore-rules \                       # skip .rules files
  -m gpt-5.5 \                          # model selection
  "your prompt here"
```

### 1.3 JSON output mode (`--json`)

```bash
codex exec --json "prompt" | jq
```

Output is **JSONL** (JSON Lines) — one JSON object per line. Event types:
- `thread.started` / `turn.started` / `turn.completed` / `turn.failed`
- `item.started` / `item.completed` — individual agent messages, reasoning, commands
- `error` — error events

Sample:
```json
{"type":"turn.completed","usage":{"input_tokens":24763,"output_tokens":122}}
```

**HaxJobs parse strategy**: Filter for `item.completed` events where `item.type == "agent_message"`, concatenate `item.text` fields, or use `-o` flag for simplicity.

### 1.4 File output (`-o`)

```bash
codex exec "prompt" -o /tmp/result.txt
```

Writes final message to file AND prints it to stdout.

### 1.5 Structured output (`--output-schema`) ⭐ KEY FEATURE

This is Codex's killer feature for HaxJobs. You supply a JSON Schema file, and Codex guarantees the final response conforms to it:

```bash
codex exec "Evaluate this job fit..." \
  --output-schema ./evaluation_schema.json \
  -o ./evaluation_result.json
```

**HaxJobs evaluation schema** (file: `evaluate/codex_schema.json`):

```json
{
  "type": "object",
  "properties": {
    "fit_score": { "type": "integer", "minimum": 0, "maximum": 100 },
    "level": { "type": "integer", "minimum": 1, "maximum": 4 },
    "level_name": { "type": "string", "enum": ["Strong Fit", "Good Fit", "Partial Fit", "Not a Fit"] },
    "role_family": { "type": "string" },
    "tech_stack_match": { "type": "integer", "minimum": 0, "maximum": 30 },
    "role_fit": { "type": "integer", "minimum": 0, "maximum": 35 },
    "level_match": { "type": "integer", "minimum": 0, "maximum": 15 },
    "location_match": { "type": "integer", "minimum": 0, "maximum": 10 },
    "company_fit": { "type": "integer", "minimum": 0, "maximum": 10 },
    "summary": { "type": "string" },
    "gaps": { "type": "array", "items": { "type": "string" } },
    "strengths": { "type": "array", "items": { "type": "string" } }
  },
  "required": ["fit_score", "level", "level_name", "summary", "gaps", "strengths"],
  "additionalProperties": false
}
```

This eliminates all JSON parsing fragility — Codex returns valid JSON or fails explicitly.

### 1.6 Stdin piping

```bash
echo "$job_description" | codex exec "Evaluate this job against the candidate profile: $(cat profile.md)" -o result.json
```

Or with `-` sentinel for stdin-as-prompt:
```bash
cat full_prompt.txt | codex exec - --output-schema schema.json -o result.json
```

---

## 2. Model Discovery

### 2.1 Model list

From `~/.codex/models_cache.json` (fetched live 2026-06-30):

| Slug | Display Name | API Support |
|------|-------------|-------------|
| `gpt-5.5` | GPT-5.5 | ✅ |
| `gpt-5.4` | GPT-5.4 | ✅ |
| `gpt-5.4-mini` | GPT-5.4-Mini | ✅ |
| `codex-auto-review` | Codex Auto Review | ✅ (hidden) |

### 2.2 Model selection

```bash
codex exec -m gpt-5.5 "prompt"            # frontier model
codex exec -m gpt-5.4-mini "prompt"       # cheaper/faster
```

Override via config:
```bash
codex exec -c model="gpt-5.4-mini" "prompt"
```

### 2.3 Reading model list from HaxJobs

```python
import json

def get_codex_models():
    cache = json.load(open(os.path.expanduser("~/.codex/models_cache.json")))
    return [
        m["slug"] for m in cache["models"]
        if m.get("supported_in_api") and m.get("visibility") == "list"
    ]
# Returns: ["gpt-5.5", "gpt-5.4", "gpt-5.4-mini"]
```

### 2.4 Reasoning effort levels

GPT-5.5 supports `low`, `medium`, `high`, `xhigh` reasoning. For evaluation (deterministic scoring), use `low` for speed or `medium` for accuracy:

```bash
# Via config override (if supported)
codex exec -c model_reasoning_effort="low" "prompt"
```

---

## 3. Authentication

### 3.1 Default: ChatGPT-managed auth

`~/.codex/auth.json` — OAuth tokens for ChatGPT account. Used by default.

### 3.2 API key auth (for cron/CI)

```bash
CODEX_API_KEY=sk-... codex exec "prompt"
```

`CODEX_API_KEY` env var is **only supported in `codex exec`** — designed for automation. API keys are simpler to provision and rotate than OAuth.

### 3.3 For Archilles (cron VPS)

```bash
# In crontab or run_pipeline.sh
export CODEX_API_KEY="$HAXJOBS_OPENAI_API_KEY"
codex exec --ephemeral --skip-git-repo-check \
  --dangerously-bypass-approvals-and-sandbox \
  -m gpt-5.5 \
  --output-schema /home/hermes/haxjobs/evaluate/codex_schema.json \
  -o /tmp/haxjobs_eval_result.json \
  "$prompt"
```

---

## 4. Rate Limit Detection

### 4.1 API key rate limits

OpenAI API key rate limits are standard RPM/TPM tiers. Codex CLI does not expose explicit rate-limit detection — errors appear in stderr.

### 4.2 Detection strategy

```python
def _is_rate_limited(stderr_output: str) -> bool:
    markers = [
        "429", "rate_limit", "rate limit", "too many requests",
        "quota exceeded", "insufficient_quota", "billing_hard_limit_reached"
    ]
    stderr_lower = stderr_output.lower()
    return any(m in stderr_lower for m in markers)
```

### 4.3 Model fallback chain

Since Codex only has OpenAI models, the fallback is limited:
1. `gpt-5.5` (primary — most capable)
2. `gpt-5.4-mini` (cheaper, different rate-limit bucket)
3. Fall back to another agent (Hermes, Claude) if both are exhausted

---

## 5. Config File

**Location**: `~/.codex/config.toml`  
**Format**: TOML

Current config (2026-06-30):
```toml
[tui]
status_line = ["model-with-reasoning", "current-dir", "run-state", "context-remaining"]

[notice.model_migrations]
"gpt-5.3-codex" = "gpt-5.4"
"gpt-5.4" = "gpt-5.5"

[features]
memories = true
```

No explicit model config — model selection is via `-m` flag or `-c model="..."` override.

---

## 6. Integration Assessment

### 6.1 HaxJobs adapter: `evaluate/agents/codex.py`

```python
import json, subprocess, tempfile, os

def call_agent(prompt: str, timeout_seconds: int = 300) -> dict | None:
    """Run Codex exec with structured output schema.
    
    Returns parsed JSON dict on success, None on failure/rate-limit.
    """
    schema_path = os.path.join(
        os.path.dirname(__file__), "..", "codex_schema.json"
    )
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        output_path = f.name
    
    try:
        result = subprocess.run(
            [
                "codex", "exec",
                "--ephemeral",
                "--skip-git-repo-check",
                "--dangerously-bypass-approvals-and-sandbox",
                "-m", "gpt-5.5",
                "--output-schema", schema_path,
                "-o", output_path,
                prompt,
            ],
            capture_output=True, text=True,
            timeout=timeout_seconds,
            env={**os.environ, "CODEX_API_KEY": os.environ.get("CODEX_API_KEY", "")}
        )
        
        if result.returncode != 0:
            if _is_rate_limited(result.stderr):
                return None  # signal to try next model
            return None
        
        with open(output_path) as f:
            return json.load(f)
    except subprocess.TimeoutExpired:
        return None
    finally:
        try:
            os.unlink(output_path)
        except OSError:
            pass

def _is_rate_limited(stderr: str) -> bool:
    markers = ["429", "rate_limit", "too many requests", "quota exceeded"]
    return any(m in stderr.lower() for m in markers)
```

### 6.2 Key advantages over other subprocess agents

| Feature | Codex | Claude Code | Gemini CLI | Hermes |
|---------|-------|-------------|------------|--------|
| Structured JSON output | ✅ `--output-schema` | ❌ | ❌ (maybe `-o json`) | ❌ |
| API key auth | ✅ `CODEX_API_KEY` | ✅ | ✅ | ✅ |
| Ephemeral mode | ✅ `--ephemeral` | ❌ | ❌ | N/A (always) |
| Skip git check | ✅ `--skip-git-repo-check` | ❌ | ❌ | N/A |
| Approval bypass | ✅ `--dangerously-...` | ✅ `-p` | ✅ `-y` | ✅ `-z` |
| JSONL streaming | ✅ `--json` | ✅ `--output-format json` | ❌ | ❌ |

### 6.3 Shipping to Codex users

Codex has a **plugin marketplace** (`.codex-plugin/plugin.json`). HaxJobs could ship as a Codex plugin:

```json
{
  "name": "haxjobs",
  "version": "0.1.0",
  "skills": ["haxjobs-evaluate", "haxjobs-report"]
}
```

But this is **not required** — the `codex exec` adapter handles automated pipeline evaluation regardless of whether the user has the plugin installed.

---

## 7. Integration Difficulty: ⭐⭐ EASY

- ✅ Purpose-built for automation (`codex exec`)
- ✅ Structured output eliminates JSON parsing fragility
- ✅ API key auth for cron/CI
- ✅ Ephemeral mode for clean runs
- ✅ Model discovery from `models_cache.json`
- ❌ Subprocess only (Rust binary, no Python API)
- ❌ Limited model selection (OpenAI-only: 3 models)
- ❌ 300s+ runtime for complex evaluation prompts

---

## 8. Sources & References

| Source | URL | Date |
|--------|-----|------|
| Official Codex non-interactive docs | https://developers.openai.com/codex/noninteractive | 2026-06-30 (fetched) |
| Codex CLI reference | https://developers.openai.com/codex/cli/reference | 2026-06-30 |
| Codex structured output guide | https://codex.danielvaughan.com/2026/06/11/codex-exec-structured-output-pipelines-output-schema-json-resume-ci-automation/ | 2026-06-11 |
| Codex CI/CD guide | https://codex.danielvaughan.com/2026/03/26/codex-cli-cicd-non-interactive/ | 2026-03-26 |
| GitHub repo | https://github.com/openai/codex | Apache-2.0 |
| Models cache | `~/.codex/models_cache.json` (local, fetched 2026-06-30T23:10) | 2026-06-30 |
| Config file | `~/.codex/config.toml` (local) | 2026-06-30 |

---

*Research completed 2026-06-30. Source: direct CLI inspection (`codex exec --help`, `~/.codex/config.toml`, `~/.codex/models_cache.json`), OpenAI official docs at developers.openai.com/codex, and community guides.*
