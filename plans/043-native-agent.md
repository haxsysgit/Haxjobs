# Plan 043: Full native agent — tool registry, prompt tiers, identity

> **Executor instructions**: Read `haxjobs_agent_lab/analysis-docs.md` first.
> This plan implements the Hermes patterns documented there: AST tool discovery,
> 3-tier prompt assembly (stable/context/volatile), SOUL.md identity loading,
> check_fn availability gating, and agent-level tool interception.
>
> Plan 039 must be complete — this plan extends `agent.py`, adds `prompt.py`,
> `registry.py`, `tools.py`, `identity.py`.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: MED (extends existing code, introduces new patterns)
- **Depends on**: 039, 040, 041, 044
- **Category**: direction
- **Planned at**: commit `07daac6`, 2026-06-30

## Why this matters

Plan 039 gave us single-turn evaluation. This plan adds multi-turn with tools (agentic scraping), 3-tier prompt assembly (Hermes' prompt stability design), tool auto-discovery (Hermes' AST pattern), and identity loading (SOUL.md). After this plan, the HaxJobs native agent is complete — plans 045 and 048 wire it into onboarding and evaluation.

## Design — copied from Hermes docs + source

| Feature | Copied from | Source |
|---------|------------|--------|
| 3-tier prompt assembly | Hermes `agent/prompt_builder.py` | stable/context/volatile tiers |
| AST tool auto-discovery | Hermes `tools/registry.py` | scan `tools/*.py` for `registry.register()` |
| `check_fn` availability gating | Hermes registry | tool absent from schemas if check fails |
| SOUL.md identity loading | Hermes `load_soul_md()` | markdown file, not inline string |
| Agent-level tool interception | Hermes `handle_function_call()` | todo/memory/delegate bypass registry |
| Message alternation enforcement | Hermes agent loop | never 2 assistants in a row |
| `SUMMARY_PREFIX` | Hermes `context_compressor.py` | "compacted content is reference-only" |

## Final file structure

```
src/haxjobs/agent/
  __init__.py       → re-exports Agent, get_prompt  (from 039)
  agent.py          → ~120 lines (run, run_structured, run_with_tools from 039 + new)
  prompts.py        → ~30 lines (template registry, from 039)
  prompt.py         → ~80 lines NEW — build_system_prompt with 3 tiers
  registry.py       → ~50 lines NEW — AST auto-discovery, check_fn, dispatch
  tools.py          → ~60 lines NEW — web_search, fetch_page, scrape_careers_page
  identity.py       → ~30 lines NEW — load soul.md + user.md + memory.md
```

Total: ~370 lines across 7 files (up from ~100 in plan 039).

## New modules

### 1. `prompt.py` — 3-tier system prompt (Hermes design)

```python
"""3-tier system prompt assembly: stable → context → volatile.
Copied from Hermes agent/prompt_builder.py design."""
from datetime import datetime, timezone


def build_system_prompt(
    identity: str,           # from ~/.haxjobs/soul.md
    memory: str = "",        # from ~/.haxjobs/memory.md
    user_profile: str = "",  # from ~/.haxjobs/user.md
    skills_index: str = "",  # from skills/*/SKILL.md frontmatter
    context_files: str = "", # from .haxjobs/AGENTS.md etc.
    platform: str = "web",   # web | cli | cron
) -> str:
    """Assemble the cached system prompt from 3 ordered tiers.
    
    Tier 1: stable  — identity, tool guidance, skills index, platform hint
    Tier 2: context — AGENTS.md, project context files  
    Tier 3: volatile — memory snapshot, user profile, timestamp
    """
    parts = [_stable_tier(identity, skills_index, platform)]
    if context_files:
        parts.append(_context_tier(context_files))
    parts.append(_volatile_tier(memory, user_profile))
    return "\n\n".join(filter(None, parts))


def _stable_tier(identity: str, skills_index: str, platform: str) -> str:
    platform_hints = {
        "web": "You are serving results to a web dashboard. Include structured data.",
        "cli": "You are running from the command line. Be concise.",
        "cron": "Running unattended. Write results to the database directly.",
    }
    sections = [identity]
    if skills_index:
        sections.append(f"## Available skills\n{skills_index}")
    sections.append(platform_hints.get(platform, platform_hints["web"]))
    return "\n\n".join(sections)


def _context_tier(context_files: str) -> str:
    return f"# Project context\n{context_files}"


def _volatile_tier(memory: str, user_profile: str) -> str:
    parts = []
    if memory:
        parts.append(f"## Memory\n{memory}")
    if user_profile:
        parts.append(f"## User profile\n{user_profile}")
    parts.append(f"Current time: {datetime.now(timezone.utc).isoformat()}")
    return "\n\n".join(parts)
```

### 2. `identity.py` — SOUL.md loading (Hermes pattern)

```python
"""Load agent identity from markdown files. Copied from Hermes load_soul_md()."""
from pathlib import Path

HAXJOBS_HOME = Path.home() / ".haxjobs"

DEFAULT_IDENTITY = """You are HaxJobs, a job search agent. Your purpose is to help a candidate 
find and apply to jobs they are qualified for. You evaluate job descriptions 
against the candidate's profile, score fit from 0-100, identify gaps, and 
generate application materials.

Be honest — false hope wastes the candidate's time. When a job is a poor fit, 
say so clearly. When it's a good fit, give specific evidence from the profile.

You are part of a deterministic pipeline. Your LLM calls handle the fuzzy parts 
(evaluation, CV extraction, scraping unstructured sites). Everything else 
(filtering, classification, pack assembly) is handled by config-driven rules."""


def load_identity() -> str:
    """Load identity from ~/.haxjobs/soul.md, fall back to default."""
    soul_path = HAXJOBS_HOME / "soul.md"
    if soul_path.exists():
        return soul_path.read_text(encoding="utf-8").strip()
    return DEFAULT_IDENTITY


def load_memory() -> str:
    """Load persistent memory from ~/.haxjobs/memory.md."""
    path = HAXJOBS_HOME / "memory.md"
    return path.read_text(encoding="utf-8").strip() if path.exists() else ""


def load_user_profile() -> str:
    """Load user profile from ~/.haxjobs/user.md."""
    path = HAXJOBS_HOME / "user.md"
    return path.read_text(encoding="utf-8").strip() if path.exists() else ""
```

### 3. `registry.py` — AST auto-discovery (Hermes pattern)

```python
"""Tool registry with AST auto-discovery. Copied from Hermes tools/registry.py."""
import ast
import importlib
from pathlib import Path
from typing import Any, Callable

ToolHandler = Callable[..., str]


class ToolEntry:
    name: str
    handler: ToolHandler
    schema: dict
    check_fn: Callable[[], bool] | None
    emoji: str


_registry: dict[str, ToolEntry] = {}


def register(
    name: str,
    handler: ToolHandler,
    schema: dict,
    *,
    check_fn: Callable[[], bool] | None = None,
    emoji: str = "🔧",
) -> None:
    """Register a tool. Called at module level in tools/*.py files."""
    _registry[name] = ToolEntry()
    _registry[name].name = name
    _registry[name].handler = handler
    _registry[name].schema = schema
    _registry[name].check_fn = check_fn
    _registry[name].emoji = emoji


def get_definitions() -> list[dict]:
    """Return OpenAI-compatible tool schemas for available tools."""
    defs = []
    for entry in _registry.values():
        if entry.check_fn is not None:
            try:
                if not entry.check_fn():
                    continue  # unavailable — skip from schemas
            except Exception:
                continue
        defs.append({"type": "function", "function": entry.schema})
    return defs


def dispatch(name: str, args: dict) -> str:
    """Execute a registered tool. Returns result string or error JSON."""
    if name not in _registry:
        return '{"error": "Unknown tool: ' + name + '"}'
    try:
        return _registry[name].handler(**args)
    except Exception as e:
        return '{"error": "Tool ' + name + ' failed: ' + str(e) + '"}'


def discover_builtin_tools(tools_dir: str | None = None) -> None:
    """Scan tools/*.py for top-level register() calls and import them.
    Uses AST to avoid importing files that don't register anything."""
    if tools_dir is None:
        tools_dir = str(Path(__file__).parent / "tools")
    tools_path = Path(tools_dir)
    if not tools_path.is_dir():
        return
    for path in sorted(tools_path.glob("*.py")):
        if path.name.startswith("_"):
            continue
        source = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "register"
            ):
                importlib.import_module(f"haxjobs.agent.tools.{path.stem}")
                break


def list_tools() -> list[str]:
    """Return names of all registered tools (for debugging)."""
    return sorted(_registry.keys())
```

### 4. `tools.py` — Built-in tools 

```python
"""Built-in tools for HaxJobs agent: web_search, fetch_page, scrape_careers_page."""
import json
import os
import urllib.request
import urllib.parse
import urllib.error
from haxjobs.agent.registry import register

# Schemas as OpenAI function definitions
WEB_SEARCH_SCHEMA = {
    "name": "web_search",
    "description": "Search the web for job listings or company career pages",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
        },
        "required": ["query"],
    },
}

FETCH_PAGE_SCHEMA = {
    "name": "fetch_page",
    "description": "Fetch and extract text content from a URL",
    "parameters": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to fetch"},
        },
        "required": ["url"],
    },
}


def web_search(query: str) -> str:
    """Search DuckDuckGo HTML (no API key needed)."""
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    # ponytail: basic search, add SERP API when free tier rate-limits
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")[:8000]
    except Exception as e:
        return json.dumps({"error": str(e)})


def fetch_page(url: str) -> str:
    """Fetch a URL and return text content."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "HaxJobs/1.0"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", errors="replace")[:16000]
    except Exception as e:
        return json.dumps({"error": str(e)})


# Register at module level — auto-discovered by registry.discover_builtin_tools()
register(
    name="web_search",
    handler=web_search,
    schema=WEB_SEARCH_SCHEMA,
    emoji="🔍",
)

register(
    name="fetch_page",
    handler=fetch_page,
    schema=FETCH_PAGE_SCHEMA,
    emoji="📄",
)
```

### 5. Agent extensions (add to existing `agent.py` from 039)

Add these methods to the Agent class:

```python
def run_with_tools(
    self,
    prompt: str,
    system: str | None = None,
    tools: list[dict] | None = None,
    max_turns: int = 5,
    temperature: float = 0.3,
) -> str:
    """Multi-turn agent loop with tool calling. Max <max_turns> iterations.
    Enforces message alternation: never two assistant messages in a row."""
    from haxjobs.agent.registry import dispatch, get_definitions
    
    if tools is None:
        tools = get_definitions()
    
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    
    for _ in range(max_turns):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools if tools else None,
            temperature=temperature,
        )
        msg = response.choices[0].message
        
        if msg.content and not msg.tool_calls:
            return _strip_code_fence(msg.content)
        
        if not msg.tool_calls:
            return msg.content or ""
        
        # Append assistant message with tool calls
        assistant_msg = {"role": "assistant", "content": msg.content or ""}
        assistant_msg["tool_calls"] = [
            {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
            for tc in msg.tool_calls
        ]
        messages.append(assistant_msg)
        
        # Execute tools and append results
        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments)
            result = dispatch(tc.function.name, args)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
    
    # Max turns exhausted — ask model for final answer
    messages.append({"role": "user", "content": "Summarize what you found."})
    final = self.client.chat.completions.create(
        model=self.model, messages=messages, temperature=temperature,
    )
    return _strip_code_fence(final.choices[0].message.content or "")
```

## Steps

### Step 1: Verify plan 039 is complete

```bash
uv run python -c "from haxjobs.agent import Agent, get_prompt; print('ok')"
```

### Step 2: Create new modules

Write `prompt.py`, `registry.py`, `tools.py`, `identity.py` as above.

### Step 3: Extend agent.py

Add `run_with_tools()` method to the existing Agent class. Add imports for `_strip_code_fence` and `dispatch`.

### Step 4: Update __init__.py

```python
from haxjobs.agent.agent import Agent, _strip_code_fence
from haxjobs.agent.prompts import get_prompt, PromptTemplate, PROMPTS
from haxjobs.agent.prompt import build_system_prompt
from haxjobs.agent.identity import load_identity, load_memory, load_user_profile
from haxjobs.agent.registry import register, dispatch, discover_builtin_tools, get_definitions
__all__ = ["Agent", "get_prompt", "build_system_prompt", "load_identity", ...]
```

### Step 5: Create soul.md + user.md defaults

```bash
mkdir -p ~/.haxjobs
# soul.md — the DEFAULT_IDENTITY from identity.py is the fallback
# user.md — written by onboarding (plan 045)
# memory.md — written by the agent after cycles (plan 057, future)
```

### Step 6: Write tests

`tests/test_agent_full.py`:

- `test_registry_register_and_dispatch` — register a mock tool, dispatch it
- `test_registry_check_fn_gates` — tool with failing check_fn excluded from schemas
- `test_tools_web_search` — mocked URL response
- `test_tools_fetch_page` — mocked URL response
- `test_build_system_prompt_tiers` — identity, context, volatile all present and ordered
- `test_build_system_prompt_no_context` — context files optional
- `test_load_identity_default` — when soul.md doesn't exist, returns default
- `test_run_with_tools_single_turn` — model returns text, no tools called
- `test_run_with_tools_one_tool_cycle` — model calls tool, agent dispatches, gets text
- `test_message_alternation` — history never has two assistant messages in a row
- `test_max_turns_exhausted` — loops max_turns times then summarizes

```bash
uv run pytest -q tests/test_agent_full.py tests/test_agent_minimal.py
```

### Step 7: Commit

```bash
git commit -m "add full native agent: AST tool registry, 3-tier prompts, soul.md identity, multi-turn"
```

## Done criteria

- [ ] `run_with_tools()` executes tool calls and returns final text
- [ ] Registry auto-discovers tools from `tools/*.py` at import time
- [ ] `check_fn` gates tool availability (failing check → tool excluded from schemas)
- [ ] `build_system_prompt()` assembles stable→context→volatile in order
- [ ] `load_identity()` reads `~/.haxjobs/soul.md`, falls back to default
- [ ] `web_search` and `fetch_page` work (mocked in tests, real in pipeline)
- [ ] Message alternation enforced in multi-turn history
- [ ] Max turns respected (default 5)
- [ ] `_strip_code_fence()` applied to all text responses
- [ ] All 11 new tests pass + all 7 plan-039 tests still pass
- [ ] Provider config from `~/.haxjobs/config.toml`

## STOP conditions

- AST discovery fails on syntax error in user tool → logged as warning, skipped
- Tool handler throws → wrapped in JSON error string, returned to model
- `_strip_code_fence()` strips too much → test with real DeepSeek output that wraps JSON in ```

## What's still deferred (plan 057 — future)

- Skill directory convention: `~/.haxjobs/skills/evaluate-job/SKILL.md`
- Skill loader with frontmatter parsing (name, description, tools whitelist)
- Skills index injection into system prompt
- Context compression (SUMMARY_PREFIX for multi-turn scraping past 5 turns)
- Provider fallback chain (DeepSeek down → try OpenAI)
