# Plan 043: Full native agent — job-search tools, prompt tiers, identity

> **Executor instructions**: Read `docs/PI_HAXJOBS_INTERNALS_MAPPING.md` first, then
> `haxjobs_agent_lab/analysis-docs.md` for the Hermes prompt-tier background.
>
> Reality update: HaxJobs is a job-search automation harness, not a coding agent.
> Mirror Pi's tool registry/dispatch pattern, not Pi's coding-tool surface. Do
> **not** add `read`, `bash`, `edit`, `write`, `grep`, `find`, or `ls` in v1.
> Keep tools domain-specific until arbitrary-site scraping or admin automation earns more.

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
- A small `run_with_tools()` loop for discovery/research tasks
- 3-tier system prompt assembly: stable/context/volatile
- `~/.haxjobs/soul.md` identity loading, with defaults

After this plan, HaxJobs can use native agentic discovery tools without becoming
a coding agent. Evaluation and onboarding still use plain `Agent.run()` with
Python passing the needed job/profile/CV text into the prompt.

## What we mirror from Pi

See `docs/PI_HAXJOBS_INTERNALS_MAPPING.md` for the complete mapping.

| Pi internal | HaxJobs Python equivalent | Decision |
|---|---|---|
| `defineTool({ name, parameters, execute })` | `registry.register(name, schema, handler, check_fn=None)` | Port |
| Built-in coding tools: `read`, `bash`, `edit`, `write`, `grep`, `find`, `ls` | Not exposed in v1 | Defer |
| Tool allowlist / `excludeTools` | `Agent(tools=[...], exclude_tools=[...])` | Port |
| `session.prompt()` tool-call loop | `Agent.run_with_tools()` | Partial port |
| Resource/context loading | `prompt.py` + `identity.py` | Partial port |
| Streaming/events/TUI/session tree | Nothing | Skip |

## Tool set

HaxJobs needs job-search-native tools first. Python services already read/write
profiles, packs, templates, and DB rows; the LLM does not need shell/filesystem
powers in v1.

| Tool | Enabled where? | Notes |
|---|---:|---|
| `web_search` | discovery only | Search for jobs/company career pages |
| `fetch_page` | discovery only | Fetch job/company pages |
| `db_query` | read-only/admin summaries | Read-only SQLite queries over HaxJobs tables |

Deferred: `read`, `write`, `edit`, `bash`, `grep`, `find`, `ls`. Add them only
when arbitrary-site scraping or user-approved admin automation needs them.

Evaluation (Plan 048) and onboarding extraction should use `Agent.run()` without tools.

## Final file structure

```
src/haxjobs/agent/
  __init__.py       → re-exports Agent, get_prompt, build_system_prompt, registry helpers
  agent.py          → extends plan 039 Agent with tools filtering + run_with_tools()
  prompts.py        → template registry, from plan 039
  prompt.py         → build_system_prompt() with stable/context/volatile tiers
  registry.py       → Pi-style ToolDef, register(), get_schemas(), dispatch()
  tools.py          → web_search, fetch_page, read-only db_query
  identity.py       → load soul.md + user.md + memory.md
```

Keep this flat. Do not add coding tools, `tools/` package, AST scanning, plugins,
or a full ResourceLoader until there is a real job-search workflow to justify it.

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

### 2. `tools.py` — job-search tools

Implement these functions and register them at module import time:

- `web_search(query)`
- `fetch_page(url)`
- `db_query(sql)`

Guardrails:

- `web_search` and `fetch_page` are for discovery/research, not evaluation.
- `fetch_page` must use a timeout, user-agent, and output truncation.
- `db_query` must reject non-read-only SQL. Accept only `SELECT`/`WITH`.
- Tool output must be truncated to keep prompts small.

Use stdlib first: `sqlite3`, `urllib.request`, `urllib.parse`. Add a
third-party dependency only if stdlib fails in a real test.

Do not add Pi coding tools (`read`, `write`, `edit`, `bash`, `grep`, `find`,
`ls`) in this plan.

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
- `test_builtin_tool_names_registered` — `web_search`, `fetch_page`, `db_query` registered
- `test_db_query_read_only`
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

- [ ] `web_search`, `fetch_page`, and read-only `db_query` are registered
- [ ] Pi coding tools (`read`, `write`, `edit`, `bash`, `grep`, `find`, `ls`) are not implemented in v1
- [ ] Tool allowlist and exclude list work
- [ ] `run_with_tools()` executes tool calls and returns final text
- [ ] Tool handlers return JSON/text error instead of raising into the model loop
- [ ] `db_query` rejects non-read SQL
- [ ] `build_system_prompt()` assembles stable→context→volatile in order
- [ ] `load_identity()` reads `~/.haxjobs/soul.md`, falls back to default
- [ ] JSON parsing remains delegated to `evaluate.common.extract_json()`
- [ ] All new tests pass + all plan-039 tests still pass
- [ ] Provider config still loads from `~/.haxjobs/haxjobs.toml`

## STOP conditions

- A coding-agent tool (`read`, `write`, `edit`, `bash`, `grep`, `find`, `ls`) appears in v1 → stop and remove it
- `db_query` accepts writes/deletes → stop and make it read-only
- Tool loop exceeds max turns without useful output → return a clear error, don't recurse

## Deferred

- SKILL.md directory loader (`~/.haxjobs/skills/*/SKILL.md`)
- Extension/plugin discovery
- Coding-agent-style tools (`read`, `write`, `edit`, `bash`, `grep`, `find`, `ls`)
- Context compression with `SUMMARY_PREFIX`
- Provider fallback chain
