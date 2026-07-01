# Plan 043: Full native agent — Pi-style tools, prompt tiers, identity

> **Executor instructions**: Read `docs/PI_HAXJOBS_INTERNALS_MAPPING.md` first, then
> `haxjobs_agent_lab/analysis-docs.md` for the Hermes prompt-tier background.
>
> Reality update: Plan 043 should mirror Pi's useful internals in Python — tool
> definitions, allow/exclude filtering, dispatch, and a small multi-turn loop. Do
> **not** copy Pi's TUI/session/event machinery, and do **not** build Hermes' full
> AST extension system yet. One flat registry and one tools module are enough.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: MED (adds tool execution; needs path/command guardrails)
- **Depends on**: 039, 040, 041, 044
- **Category**: direction
- **Planned at**: commit `07daac6`, 2026-06-30

## Why this matters

Plan 039 gave us a single-turn `Agent.run()`. This plan adds the Python
internal equivalent of Pi's agent core:

- Pi-style tool definitions: `name + JSON schema + handler + optional check_fn`
- Pi-style tool filtering: allowlist/exclude list per agent run
- Pi-style dispatch: model calls a tool by name; registry executes it
- A small `run_with_tools()` loop for multi-turn discovery/maintenance tasks
- 3-tier system prompt assembly: stable/context/volatile
- `~/.haxjobs/soul.md` identity loading, with defaults

After this plan, HaxJobs can use the same agent for evaluation, discovery,
onboarding, and admin/pipeline tasks while still keeping dangerous tools disabled
unless explicitly requested.

## What we mirror from Pi

See `docs/PI_HAXJOBS_INTERNALS_MAPPING.md` for the complete mapping.

| Pi internal | HaxJobs Python equivalent | Decision |
|---|---|---|
| `defineTool({ name, parameters, execute })` | `registry.register(name, schema, handler, check_fn=None)` | Port |
| Built-in tools: `read`, `bash`, `edit`, `write`, `grep`, `find`, `ls` | Same names in `tools.py`, with HaxJobs path/command guards | Port |
| Tool allowlist / `excludeTools` | `Agent(tools=[...], exclude_tools=[...])` | Port |
| `session.prompt()` tool-call loop | `Agent.run_with_tools()` | Partial port |
| Resource/context loading | `prompt.py` + `identity.py` | Partial port |
| Streaming/events/TUI/session tree | Nothing | Skip |

## Tool set

HaxJobs needs Pi's file/process/search primitives plus job-search-native tools.

| Tool | Enabled by default? | Notes |
|---|---:|---|
| `read` | yes | Read profile, templates, reports, generated packs, config snippets |
| `grep` | yes | Search repo/runtime text with `rg`/stdlib fallback |
| `find` | yes | Locate CV variants, pack files, reports, templates |
| `ls` | yes | List directories/artifacts |
| `web_search` | discovery only | Search for jobs/company career pages |
| `fetch_page` | discovery only | Fetch job/company pages |
| `db_query` | read-only | Read-only SQLite queries over HaxJobs tables |
| `write` | explicit only | Generate drafts/artifacts; path-guarded |
| `edit` | explicit only | Precise replacements only; path-guarded |
| `bash` | explicit only | Approved repo commands only; timeout; no secrets printing |

Evaluation (Plan 048) should use `Agent.run()` without tools unless a specific
read-only tool is explicitly needed.

## Final file structure

```
src/haxjobs/agent/
  __init__.py       → re-exports Agent, get_prompt, build_system_prompt, registry helpers
  agent.py          → extends plan 039 Agent with tools filtering + run_with_tools()
  prompts.py        → template registry, from plan 039
  prompt.py         → build_system_prompt() with stable/context/volatile tiers
  registry.py       → Pi-style ToolDef, register(), get_schemas(), dispatch()
  tools.py          → 7 Pi mirror tools + web_search/fetch_page/db_query
  identity.py       → load soul.md + user.md + memory.md
```

Keep this flat. Do not add `tools/` package, AST scanning, plugins, or a full
ResourceLoader until there is a real external tool package to load.

## New modules

### 1. `registry.py` — Pi-style tool registry

```python
"""Small tool registry — Python equivalent of Pi's defineTool + dispatch."""
from dataclasses import dataclass
from typing import Callable, Any
import json

ToolHandler = Callable[..., Any]


@dataclass
class ToolDef:
    name: str
    schema: dict
    handler: ToolHandler
    check_fn: Callable[[], bool] | None = None

    def available(self) -> bool:
        if self.check_fn is None:
            return True
        try:
            return bool(self.check_fn())
        except Exception:
            return False


TOOLS: dict[str, ToolDef] = {}


def register(name: str, schema: dict, handler: ToolHandler, check_fn=None) -> None:
    TOOLS[name] = ToolDef(name=name, schema=schema, handler=handler, check_fn=check_fn)


def get_schemas(names: list[str] | None = None, exclude: list[str] | None = None) -> list[dict]:
    allowed = set(names) if names else None
    denied = set(exclude or [])
    out = []
    for name, tool in TOOLS.items():
        if allowed is not None and name not in allowed:
            continue
        if name in denied or not tool.available():
            continue
        out.append({"type": "function", "function": tool.schema})
    return out


def dispatch(name: str, args: dict) -> str:
    tool = TOOLS.get(name)
    if tool is None:
        return json.dumps({"error": f"Unknown tool: {name}"})
    if not tool.available():
        return json.dumps({"error": f"Tool unavailable: {name}"})
    try:
        result = tool.handler(**args)
        return result if isinstance(result, str) else json.dumps(result)
    except Exception as e:
        return json.dumps({"error": f"Tool {name} failed: {e}"})
```

### 2. `tools.py` — Pi mirrors + HaxJobs tools

Implement these functions and register them at module import time:

- `read(path, limit=20000)`
- `write(path, content)`
- `edit(path, old, new)`
- `bash(command, timeout=60)`
- `grep(pattern, path=".")`
- `find(pattern="*", path=".")`
- `ls(path=".")`
- `web_search(query)`
- `fetch_page(url)`
- `db_query(sql)`

Guardrails:

- File tools only operate inside approved roots: repo root, `~/.haxjobs`, and
  configured runtime output dirs.
- `bash` must have a timeout and deny obvious foot-guns/secrets (`sudo`, `rm -rf`,
  `.env`, `git push`, `curl | sh`, etc.). Keep it explicit-only.
- `db_query` must reject non-read-only SQL. Accept only `SELECT`/`WITH`.
- Tool output must be truncated to keep prompts small.

Use stdlib first: `pathlib`, `subprocess.run`, `sqlite3`, `urllib.request`. Add a
third-party dependency only if stdlib fails in a real test.

### 3. `prompt.py` — 3-tier system prompt

```python
"""3-tier system prompt assembly: stable → context → volatile."""
from datetime import datetime, timezone


def build_system_prompt(
    identity: str,
    memory: str = "",
    user_profile: str = "",
    skills_index: str = "",
    context_files: str = "",
    platform: str = "web",
) -> str:
    parts = [_stable_tier(identity, skills_index, platform)]
    if context_files:
        parts.append(f"# Project context\n{context_files}")
    volatile = []
    if memory:
        volatile.append(f"## Memory\n{memory}")
    if user_profile:
        volatile.append(f"## User profile\n{user_profile}")
    volatile.append(f"Current time: {datetime.now(timezone.utc).isoformat()}")
    parts.append("\n\n".join(volatile))
    return "\n\n".join(parts)


def _stable_tier(identity: str, skills_index: str, platform: str) -> str:
    hints = {
        "web": "You are serving HaxJobs results to a web dashboard.",
        "cli": "You are running from the command line. Be concise.",
        "cron": "Running unattended. Write results to durable storage.",
    }
    parts = [identity, hints.get(platform, hints["web"])]
    if skills_index:
        parts.append(f"## Available skills\n{skills_index}")
    return "\n\n".join(parts)
```

### 4. `identity.py` — `soul.md`, `memory.md`, `user.md`

```python
from pathlib import Path

HAXJOBS_HOME = Path.home() / ".haxjobs"

DEFAULT_IDENTITY = """You are HaxJobs, a job search agent. Your purpose is to help a candidate find and apply to jobs they are qualified for.
Be honest: false hope wastes the candidate's time. When a job is a poor fit, say so clearly. When it is a good fit, cite evidence from the profile.
Never submit applications or send outreach without explicit user approval."""


def _read(name: str) -> str:
    path = HAXJOBS_HOME / name
    return path.read_text(encoding="utf-8").strip() if path.exists() else ""


def load_identity() -> str:
    return _read("soul.md") or DEFAULT_IDENTITY


def load_memory() -> str:
    return _read("memory.md")


def load_user_profile() -> str:
    return _read("user.md")
```

### 5. Extend `agent.py`

- Add constructor parameters: `tools: list[str] | None = None`,
  `exclude_tools: list[str] | None = None`.
- Import `haxjobs.agent.tools` once so module-level registrations run.
- Add `run_with_tools()` with `max_turns=5`.
- Keep `run()` unchanged for single-turn evaluation.
- Callers who need JSON still use `evaluate.common.extract_json()`.

Sketch:

```python
def run_with_tools(self, prompt: str, system: str | None = None, max_turns: int = 5, temperature: float = 0.3) -> str:
    from haxjobs.agent.registry import dispatch, get_schemas
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    schemas = get_schemas(self.tools, self.exclude_tools)

    for _ in range(max_turns):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=schemas or None,
            temperature=temperature,
        )
        msg = response.choices[0].message
        if not msg.tool_calls:
            return msg.content or ""

        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ],
        })
        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments or "{}")
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": dispatch(tc.function.name, args)})

    return "Max tool turns reached. Run again with a narrower task."
```

## Steps

### Step 1: Verify plan 039 is complete

```bash
uv run python -c "from haxjobs.agent import Agent, get_prompt; print('ok')"
```

### Step 2: Create new modules

Write `registry.py`, `tools.py`, `prompt.py`, and `identity.py` as above.

### Step 3: Extend `agent.py`

Add tool allow/exclude fields and `run_with_tools()`. Keep `run()` as the simple
single-turn path.

### Step 4: Update `__init__.py`

Export:

```python
Agent, get_prompt, PromptTemplate, PROMPTS,
build_system_prompt,
load_identity, load_memory, load_user_profile,
register, dispatch, get_schemas, TOOLS
```

### Step 5: Write tests

`tests/test_agent_full.py`:

- `test_registry_register_and_dispatch`
- `test_registry_check_fn_gates`
- `test_get_schemas_allowlist_and_exclude`
- `test_builtin_tool_names_registered` — all 10 tools registered
- `test_file_tools_path_guard`
- `test_db_query_read_only`
- `test_bash_denylist`
- `test_build_system_prompt_tiers`
- `test_load_identity_default`
- `test_run_with_tools_single_turn`
- `test_run_with_tools_one_tool_cycle`
- `test_max_turns_exhausted`

```bash
uv run pytest -q tests/test_agent_full.py tests/test_agent_minimal.py
```

### Step 6: Commit

```bash
git commit -m "add full native agent with Pi-style tool registry"
```

## Done criteria

- [ ] `read`, `write`, `edit`, `bash`, `grep`, `find`, `ls` are registered
- [ ] `web_search`, `fetch_page`, and read-only `db_query` are registered
- [ ] Tool allowlist and exclude list work
- [ ] `run_with_tools()` executes tool calls and returns final text
- [ ] Tool handlers return JSON/text error instead of raising into the model loop
- [ ] File tools enforce approved-root path guardrails
- [ ] `bash` has timeout + denylist and is not enabled by automated evaluation
- [ ] `db_query` rejects non-read SQL
- [ ] `build_system_prompt()` assembles stable→context→volatile in order
- [ ] `load_identity()` reads `~/.haxjobs/soul.md`, falls back to default
- [ ] JSON parsing remains delegated to `evaluate.common.extract_json()`
- [ ] All new tests pass + all plan-039 tests still pass
- [ ] Provider config still loads from `~/.haxjobs/haxjobs.toml`

## STOP conditions

- A tool can read/write outside approved roots → stop and fix path guard before continuing
- `bash` can print `.env`/secrets or run destructive commands → stop and tighten guardrails
- `db_query` accepts writes/deletes → stop and make it read-only
- Tool loop exceeds max turns without useful output → return a clear error, don't recurse

## Deferred

- SKILL.md directory loader (`~/.haxjobs/skills/*/SKILL.md`)
- Extension/plugin discovery
- AST scanning for external tool modules
- Context compression with `SUMMARY_PREFIX`
- Provider fallback chain
