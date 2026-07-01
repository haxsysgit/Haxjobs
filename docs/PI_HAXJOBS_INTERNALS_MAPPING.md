# Pi → HaxJobs Agent Internals Mapping

This is the source-of-truth mapping for Plan 043. HaxJobs should mirror Pi's useful internals in Python, not copy Pi's TUI/session machinery.

## Core internals

| Pi internal | HaxJobs Python equivalent | Decision |
|---|---|---|
| `defineTool({ name, parameters, execute })` | `registry.register(name, schema, handler, check_fn=None)` | Port |
| TypeBox schemas | Plain JSON Schema `dict` in OpenAI function-call format | Port without dependency |
| Built-in tool factories (`createReadTool`, `createBashTool`, etc.) | `tools.py` registers repo/job-search tools with cwd/path guards | Port |
| Tool allowlist (`tools: [...]`) | `Agent(..., tools=[...])` / `get_schemas(names=...)` | Port |
| `excludeTools` | `Agent(..., exclude_tools=[...])` / schema filtering | Port |
| Tool dispatch by name | `dispatch(name, args) -> str` | Port |
| `createAgentSession().prompt()` | `Agent.run()` and `Agent.run_with_tools()` | Partial port |
| `AgentState.messages` | Local OpenAI-format `messages: list[dict]` inside `run_with_tools()` | Port |
| `state.systemPrompt` | `build_system_prompt()` output | Port |
| ResourceLoader context files | Minimal `identity.py` / `prompt.py` loaders | Partial port |
| SKILL.md discovery | Deferred `~/.haxjobs/skills/*/SKILL.md` loader | Defer |
| AuthStorage / ModelRegistry | Existing provider setup service + env fallback | Partial port |
| Event streaming | Logging only | Skip |
| TUI / InteractiveMode | FastAPI + React dashboard | Skip |
| SessionManager JSONL tree | SQLite + pipeline run state | Skip |
| Compaction | Not needed for v1 single/few-turn runs | Defer |
| Extensions API | Not needed until users need third-party tools | Defer |
| MCP | Not needed | Skip |

## Tool set

HaxJobs needs Pi's file/process/search primitives plus job-search-native tools.

| Tool | Mirrors Pi? | Purpose in HaxJobs |
|---|---:|---|
| `read` | Yes | Read profile JSON, CV variants, templates, generated packs, config snippets |
| `write` | Yes | Write drafts, generated artifacts, controlled config/profile updates |
| `edit` | Yes | Precise text replacement in templates/profile/config files |
| `bash` | Yes | Run approved repo commands: tests, pipeline commands, scraper commands |
| `grep` | Yes | Search repo files, templates, reports, generated packs |
| `find` | Yes | Locate CV variants, templates, reports, pack files |
| `ls` | Yes | List directories/artifacts |
| `web_search` | No | Find job listings/company career pages |
| `fetch_page` | No | Fetch job descriptions/company pages |
| `db_query` | No | Read-only SQLite queries over jobs/evaluations/decisions |

## Safety policy

- Tools are not globally enabled for every task.
- Evaluation (`Plan 048`) should use `Agent.run()` without tools unless a specific evaluator needs a read-only tool.
- Discovery may use `web_search`, `fetch_page`, and read-only DB/file tools.
- `bash`, `write`, and `edit` are admin tools: enable only for explicit maintenance/pipeline tasks.
- File tools must stay inside approved roots: repo root, `~/.haxjobs`, and configured runtime output directories.
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
# agent.py
agent = Agent(tools=["read", "grep", "find", "ls"])
text = agent.run_with_tools("Find generated packs for Faculty jobs")
```

Keep it boring: one registry, one tools module, one loop. Add extension discovery only when a real external tool package exists.
