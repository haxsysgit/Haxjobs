# Pi → HaxJobs Agent Internals Mapping

This is the source-of-truth mapping for Plan 043. HaxJobs is a job-search automation harness built on top of the HaxJobs app — not a coding agent. We mirror Pi's useful harness internals, not Pi's coding-tool surface.

## Core internals

| Pi internal | HaxJobs Python equivalent | Decision |
|---|---|---|
| `defineTool({ name, parameters, execute })` | `registry.register(name, schema, handler, check_fn=None)` | Port |
| TypeBox schemas | Plain JSON Schema `dict` in OpenAI function-call format | Port without dependency |
| Tool allowlist (`tools: [...]`) | `Agent(..., tools=[...])` / `get_schemas(names=...)` | Port |
| `excludeTools` | `Agent(..., exclude_tools=[...])` / schema filtering | Port |
| Tool dispatch by name | `dispatch(name, args) -> str` | Port |
| `createAgentSession().prompt()` | `Agent.run()` and `Agent.run_with_tools()` | Partial port |
| `AgentState.messages` | Local OpenAI-format `messages: list[dict]` inside `run_with_tools()` | Port |
| `state.systemPrompt` | `build_system_prompt()` output | Port |
| ResourceLoader context files | Minimal `identity.py` / `prompt.py` loaders | Partial port |
| AuthStorage / ModelRegistry | Existing provider setup service + env fallback | Partial port |
| Built-in coding tools (`read`, `bash`, `edit`, `write`, `grep`, `find`, `ls`) | Not exposed to the HaxJobs agent in v1 | Defer |
| SKILL.md discovery | Deferred `~/.haxjobs/skills/*/SKILL.md` loader | Defer |
| Event streaming | Logging only | Skip |
| TUI / InteractiveMode | FastAPI + React dashboard | Skip |
| SessionManager JSONL tree | SQLite + pipeline run state | Skip |
| Compaction | Not needed for v1 single/few-turn runs | Defer |
| Extensions API | Not needed until users need third-party tools | Defer |
| MCP | Not needed | Skip |

## V1 tool set

Keep v1 boring: just enough for job-search automation. Python services still read/write DB/files directly; the LLM does not need shell/file-system powers for normal evaluation or onboarding.

| Tool | Purpose in HaxJobs |
|---|---|
| `web_search` | Find job listings/company career pages when existing scrapers are not enough |
| `fetch_page` | Fetch job descriptions/company pages for extraction |
| `db_query` | Read-only SQLite queries over jobs/evaluations/decisions for summaries/debugging |

## Deferred tool set

These are Pi coding-agent tools. Do not build them in Plan 043. Add only when a concrete job-search workflow needs them — e.g. arbitrary new-site scraping, controlled maintenance automation, or user-approved admin tasks.

| Deferred tool | Add when |
|---|---|
| `read` | The agent must inspect user-approved local artifacts directly instead of receiving them from service code |
| `write` | The agent must create approved artifacts outside existing pack/profile services |
| `edit` | The agent must patch user-approved templates/configs |
| `bash` | The agent must run approved maintenance/pipeline commands, with strict allowlist + timeout |
| `grep` / `find` / `ls` | The agent needs filesystem exploration for a real workflow |

## Safety policy

- Evaluation (`Plan 048`) should use `Agent.run()` without tools.
- Onboarding extraction should use `Agent.run()` without tools; Python passes CV/profile text in.
- Discovery may use `web_search`, `fetch_page`, and read-only `db_query`.
- No `bash`, `write`, `edit`, or filesystem exploration tools in v1.
- `db_query` is read-only in v1.
- Sending applications/outreach remains forbidden without explicit user approval.

## Minimal Python shape

```python
# registry.py
@dataclass
class ToolDef:
    name: str
    schema: dict
    handler: Callable[..., str]
    check_fn: Callable[[], bool] | None = None

TOOLS: dict[str, ToolDef] = {}

def register(name: str, schema: dict, handler, check_fn=None) -> None: ...
def get_schemas(names=None, exclude=None) -> list[dict]: ...
def dispatch(name: str, args: dict) -> str: ...
```

```python
# discovery only
agent = Agent(tools=["web_search", "fetch_page"])
text = agent.run_with_tools("Find current backend engineering jobs at Faculty AI")
```

Keep it boring: one registry, one tools module, one loop. Add coding-style tools only after a real HaxJobs workflow earns them.
