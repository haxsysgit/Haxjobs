# Plan 043: HaxJobs native agent — agent loop, tool registry, tool API

> **Executor instructions**: Follow this plan step by step. Run every verification command and confirm the expected result before moving to the next step. If anything in the "STOP conditions" section occurs, stop and report — do not improvise. When done, update the status row for this plan in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat bf83142..HEAD -- src/haxjobs/`
> Plans 040 (package), 041 (FastAPI), and 042 (provider setup) must be complete.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: MED (foundational — every LLM interaction flows through this)
- **Depends on**: 039, 040, 041, 042
- **Category**: direction
- **Planned at**: commit `bf83142`, 2026-06-30

## Why this matters

Plan 039 delivered the bare-minimum agent: `Agent.run()` and `Agent.run_structured()` — single-turn, no tools. This plan adds what makes it a real agent: multi-turn conversation, tool calling, and a tool registry. The old `evaluate/agents/` directory tried to solve this by spawning agent CLIs as subprocess — wrong direction.

This plan extends `src/haxjobs/agent/agent.py` with:
1. Multi-turn loop with tool calling (adds to the `run()` method from 039)
2. Tool registry (`registry.py`) — decorator-based, any module can register tools
3. Built-in tools (`tools.py`) — `web_search`, `fetch_page`

Nothing from plan 039 gets deleted. This plan extends the Agent class with new methods and adds new modules alongside the existing one.

## Design

```
src/haxjobs/agent/
  __init__.py     # re-exports
  agent.py        # Agent class: run(), run_with_tools()
  registry.py     # ToolRegistry: @tool decorator, register, list_tools()
  tools.py        # Built-in tools: web_search, fetch_page, scrape_url
```

### Agent class

```python
class Agent:
    def __init__(self, model: str | None = None):
        cfg = load_provider_config()  # from ~/.haxjobs/config.toml
        self.client = OpenAI(
            api_key=cfg["provider"]["api_key"],
            base_url=cfg["provider"]["base_url"],
        )
        self.model = model or cfg["provider"]["model"]
        self.max_turns = 10
        self.context_limit = 128_000  # tokens — safe for most models

    def run(
        self,
        prompt: str,
        system: str | None = None,
        tools: list[dict] | None = None,
        max_turns: int | None = None,
        temperature: float = 0.3,
    ) -> str:
        """Run agent with optional tools. Returns final text response."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        tool_map = {}
        if tools:
            from haxjobs.agent.registry import get_registry
            tool_map = {t["function"]["name"]: get_registry().get_tool(t["function"]["name"]) for t in tools}

        for _ in range(max_turns or self.max_turns):
            kwargs = {"model": self.model, "messages": messages, "temperature": temperature}
            if tools:
                kwargs["tools"] = tools

            response = self.client.chat.completions.create(**kwargs)
            msg = response.choices[0].message

            if msg.tool_calls:
                messages.append({"role": "assistant", "tool_calls": msg.tool_calls})
                for tc in msg.tool_calls:
                    fn = tool_map.get(tc.function.name)
                    if fn:
                        import json
                        args = json.loads(tc.function.arguments)
                        result = fn(**args)
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": str(result),
                        })
            else:
                return msg.content or ""

        return messages[-1].get("content", "") if messages else ""

    def run_structured(
        self,
        prompt: str,
        system: str | None = None,
        json_schema: dict | None = None,
        temperature: float = 0.3,
    ) -> dict:
        """Run agent expecting structured JSON output. No tools."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        kwargs = {"model": self.model, "messages": messages, "temperature": temperature}
        if json_schema:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "response", "schema": json_schema},
            }

        response = self.client.chat.completions.create(**kwargs)
        import json
        return json.loads(response.choices[0].message.content)
```

### Tool registry

```python
"""Tool registry — decorator-based, any module can register tools."""

_registry: "ToolRegistry | None" = None


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, callable] = {}
        self._schemas: dict[str, dict] = {}

    def register(self, name: str, description: str, parameters: dict):
        """Decorator: register a tool function."""
        def decorator(fn):
            self._tools[name] = fn
            self._schemas[name] = {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": parameters,
                },
            }
            return fn
        return decorator

    def get_tool(self, name: str) -> callable | None:
        return self._tools.get(name)

    def get_schemas(self, names: list[str] | None = None) -> list[dict]:
        if names:
            return [self._schemas[n] for n in names if n in self._schemas]
        return list(self._schemas.values())


def get_registry() -> ToolRegistry:
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry
```

### Built-in tools

```python
"""Built-in tools for the HaxJobs agent."""

from haxjobs.agent.registry import get_registry

_registry = get_registry()


@_registry.register(
    name="web_search",
    description="Search the web for job listings, company careers pages, or hiring information",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
        },
        "required": ["query"],
    },
)
def web_search(query: str) -> str:
    # ponytail: use requests + DuckDuckGo HTML scraping, no API key needed
    import requests
    try:
        resp = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": "HaxJobs/1.0"},
            timeout=10,
        )
        # Extract result snippets...
        return resp.text[:4000]
    except Exception as e:
        return f"Search failed: {e}"


@_registry.register(
    name="fetch_page",
    description="Fetch and extract text content from a URL (careers page, job listing, company site)",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to fetch"},
        },
        "required": ["url"],
    },
)
def fetch_page(url: str) -> str:
    import requests
    try:
        resp = requests.get(url, headers={"User-Agent": "HaxJobs/1.0"}, timeout=15)
        # Strip HTML tags for text extraction
        import re
        text = re.sub(r"<[^>]+>", " ", resp.text)
        text = re.sub(r"\s+", " ", text)
        return text[:8000]
    except Exception as e:
        return f"Fetch failed: {e}"
```

### Usage pattern — how other modules call the agent

```python
from haxjobs.agent import Agent

agent = Agent()  # reads config from ~/.haxjobs/config.toml

# Structured output (evaluation, CV extraction)
result = agent.run_structured(
    prompt="Evaluate this job against the profile...",
    system="You are a job-candidate fit evaluator...",
    json_schema={...},
)

# Tool-using (scraper discovery, job research)
from haxjobs.agent.registry import get_registry
tools = get_registry().get_schemas(["web_search", "fetch_page"])
result = agent.run(
    prompt="Find the careers page for Monzo and list all engineering roles...",
    system="You are a job discovery agent...",
    tools=tools,
)
```

## Steps

### Step 1: Extend Agent class with multi-turn tool loop

Add to the existing `src/haxjobs/agent/agent.py` from plan 039. The `__init__`, `run()`, `run_structured()`, and `_load_provider_config()` already exist. Add the tool-calling variant:

New method `run_with_tools()` added to the Agent class. The existing `run()` and `run_structured()` methods stay unchanged for simple single-turn use.

**Verify**: `uv run python -c "from haxjobs.agent import Agent; a = Agent(); print(hasattr(a, 'run_with_tools'))"` → True

### Step 2: Create registry.py and tools.py

Create `src/haxjobs/agent/registry.py` and `src/haxjobs/agent/tools.py` as shown in the Design section above. Update `__init__.py` to export the new symbols.

### Step 3: Wire provider config loading reference

Ensure the config loading in agent.py matches plan 039's `_load_provider_config()`:

```python
def load_provider_config() -> dict:
    """Load provider config from ~/.haxjobs/config.toml.
    Falls back to env vars: DEEPSEEK_API_KEY, OPENAI_API_KEY."""
    import os
    from pathlib import Path
    import tomllib

    config_path = Path.home() / ".haxjobs" / "config.toml"
    if config_path.exists():
        with open(config_path, "rb") as f:
            return tomllib.load(f)

    # Fallback: env vars
    if os.getenv("DEEPSEEK_API_KEY"):
        return {
            "provider": {
                "name": "deepseek",
                "api_key": os.getenv("DEEPSEEK_API_KEY"),
                "base_url": "https://api.deepseek.com",
                "model": "deepseek-chat",
            }
        }
    raise RuntimeError("No provider configured. Run haxjobs start and visit /setup.")
```

### Step 4: Write tests

`tests/test_agent.py`:
- `test_agent_init_from_config` — loads from temp config.toml
- `test_agent_init_from_env` — falls back to DEEPSEEK_API_KEY
- `test_agent_run_structured` — mocks OpenAI call, returns structured dict
- `test_agent_run_with_tools` — mocks tool call loop
- `test_tool_registry_register` — decorator stores tool
- `test_tool_registry_get_schemas` — returns OpenAI-compatible tool schemas
- `test_builtin_tools_exist` — web_search and fetch_page registered

```bash
uv run pytest -q tests/test_agent.py
```

### Step 5: Commit

```bash
git commit -m "add HaxJobs native agent: loop, tool registry, built-in tools"
```

## Done criteria

- [ ] `Agent.run()` returns text from mocked LLM
- [ ] `Agent.run_structured()` returns dict from validated JSON schema
- [ ] Tool registry stores and retrieves tools by name
- [ ] `web_search` and `fetch_page` registered as built-in tools
- [ ] Provider config loaded from `~/.haxjobs/config.toml`
- [ ] Falls back to `DEEPSEEK_API_KEY` env var
- [ ] 5+ tests pass
- [ ] `openai` already in deps from plan 039

## STOP conditions

- `from openai import OpenAI` fails — `uv add openai` didn't run
- Tool decorator causes import-time side effects — ensure registry is lazy-initialized
- DeepSeek API returns different tool call format than OpenAI — test with real call if mocked tests pass but real fails
