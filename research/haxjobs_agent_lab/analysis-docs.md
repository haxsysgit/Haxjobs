# HaxJobs Agent Design — Documentation-Backed Analysis

Combined from Hermes official docs + source code + Pi source analysis.
Sources: `pi-source/`, `hermes-source/`, and `hermes-agent.nousresearch.com/docs/developer-guide/`

## Design principles to steal (in order of importance)

### 1. Prompt stability — Hermes' backbone (STEAL WHOLE)

Hermes deliberately separates **cached system prompt** from **API-call-time additions**. This is their most important design choice.

```
Cached system prompt (built once, cached):
  Tier 1: stable  — SOUL.md identity, tool/model guidance, skills prompt
  Tier 2: context — project context files (AGENTS.md, .hermes.md)
  Tier 3: volatile — MEMORY.md snapshot, USER.md snapshot, timestamp

API-call-time only (NOT persisted):
  - ephemeral_system_prompt
  - prefill messages
  - turn-specific overlays
```

For HaxJobs, this maps to:

```
Cached (built once per evaluation cycle):
  Tier 1: stable  — HaxJobs identity ("you are a job-candidate evaluator"), 
                     evaluation rubric, scoring guidance
  Tier 2: context — profile.json facts (immutable for this cycle)
  Tier 3: volatile — timestamp, model/provider info

Per-job (NOT cached):
  - job description text
  - company-specific notes from profile.json
  - specific evaluation instructions for this role
```

**Why this matters**: If evaluation instructions change per job, the entire cached prefix breaks. Hermes solved this by keeping the stable stuff stable and injecting per-turn stuff at call time. HaxJobs should do the same — the evaluation rubric is stable, the job description is per-turn.

### 2. SOUL.md — behavior as a file, not code (STEAL WHOLE)

Hermes explicitly tells users: "edit SOUL.md, don't edit prompt_builder.py." The agent's identity and standing behavior lives in a markdown file. HaxJobs equivalent:

```
~/.haxjobs/
  soul.md          → "You are HaxJobs, a job search agent. Your purpose is..."
  memory.md        → "User applied to 3 backend roles last cycle, prefers..."
  user.md          → "Name: Arinze, GitHub: haxsysgit, needs visa sponsorship"
  evaluate-job/
    SKILL.md       → evaluation rubric + system prompt
  discover-jobs/
    SKILL.md       → discovery instructions + scraping guidance
```

### 3. Tool auto-discovery via AST (STEAL PATTERN)

Hermes scans `tools/*.py` at import time, finds files with top-level `registry.register()` calls, and imports them. No manual import list.

```python
def discover_builtin_tools(tools_dir=None):
    tools_path = Path(tools_dir) if tools_dir else Path(__file__).parent
    for path in sorted(tools_path.glob("*.py")):
        if path.name in {"__init__.py", "registry.py"}:
            continue
        if _module_registers_tools(path):  # AST check
            importlib.import_module(f"haxjobs.tools.{path.stem}")
```

HaxJobs version: scan `~/.haxjobs/tools/` for drop-in tool modules. User writes `serpapi_search.py` → auto-picked up.

### 4. check_fn — availability gating (STEAL WHOLE)

Each tool has an optional `check_fn`:

```python
registry.register(
    name="web_search",
    schema={...},
    handler=web_search,
    check_fn=lambda: bool(os.environ.get("SERP_API_KEY")),
)
```

If SERP_API_KEY isn't set, web_search doesn't appear in tool schemas sent to the LLM. The LLM never knows the tool exists, so it never tries to call it.

### 5. Agent-level tools bypass the registry (STEAL PATTERN)

Four Hermes tools (todo, memory, session_search, delegate_task) are intercepted before reaching `registry.dispatch()` because they need agent state. This pattern is useful for HaxJobs tools that need DB access:

```python
# HaxJobs agent-level tools
AGENT_TOOLS = {"save_evaluation", "build_pack", "mark_applied"}

def handle_tool_call(name, args, agent):
    if name in AGENT_TOOLS:
        return _handle_agent_tool(name, args, agent)  # has DB access
    return registry.dispatch(name, args)  # stateless tool
```

### 6. Platform hints — surface-specific instructions (STEAL PATTERN)

Hermes injects different guidance for CLI vs Telegram vs Slack. HaxJobs equivalent:

```
CLI mode:     "You are evaluating jobs from the command line. Be brief."
Web UI mode:  "Results will render in a dashboard. Include structured data."
Cron mode:    "Running unattended. Write results to the database directly."
```

## What Pi contributes that Hermes doesn't

| Aspect | Hermes | Pi | HaxJobs takes |
|--------|--------|----|---------------|
| Prompt assembly | 3-tier cached + ephemeral | Skills + AGENTS.md injection | Hermes' tier system |
| Tool registration | AST auto-discovery + 70 tools | Switch statement + 7 tools | AST discovery from Hermes, count from Pi |
| Identity | SOUL.md file | SKILL.md frontmatter | SOUL.md pattern from Hermes |
| Context files | AGENTS.md, .hermes.md | AGENTS.md, SKILL.md | Both — load from project dir |
| Philosophy | Platform-agnostic core | Get out of the LLM's way | Pi's minimalism, Hermes' structure |
| Multi-turn | Full conversation loop | Stateless turns | Hermes' single-turn pattern, not full loop |

## Revised HaxJobs agent architecture

```
haxjobs/agent/
  __init__.py
  agent.py          → ~100 lines (run, run_structured, run_with_tools, _handle_agent_tool)
  prompt.py         → ~80 lines (build_system_prompt with tiers: stable/context/volatile)
  registry.py       → ~40 lines (AST auto-discovery, check_fn, dispatch)
  tools.py          → ~50 lines (web_search, fetch_page, scrape_careers_page)
  config.py         → ~20 lines (load from ~/.haxjobs/config.toml)
  identity.py       → ~30 lines (load soul.md + user.md + memory.md)

Total core: ~320 lines

~/.haxjobs/
  config.toml       → provider config (plan 042)
  soul.md           → "You are HaxJobs..." (plan 043)
  user.md           → profile snapshot (plan 045)
  memory.md         → persistent facts (plan 057)
  skills/           → per-mode system prompts (plan 057)
    evaluate-job/SKILL.md
    discover-jobs/SKILL.md
  tools/            → user-installed tools (post-v1)
```

## What changed from the source-only analysis

| Previous assumption | Docs correction |
|-----|-----|
| Hermes' `run_oneshot()` is the pattern to copy | The **prompt stability design** (cached vs ephemeral) is more fundamental — `run_oneshot` is just a consumer of it |
| Tool decorator (plan 043) | **AST auto-discovery** is cleaner — no decorators, just `registry.register()` at module level |
| Skip Hermes' context compressor | Agreed, but note that the 50% context threshold triggers preflight compression — HaxJobs needs this too when scraping 10+ pages |
| `_strip_code_fence()` is a one-liner | Correct — docs confirm models wrap JSON in fenced code blocks |
| Skip Hermes' conversation loop entirely | Agreed, but steal the **message alternation enforcement** (never two assistant messages in a row) for multi-turn scraping in plan 043 |
| Provider abstraction via config.toml | Confirmed — Hermes' 3 API modes (chat, codex, anthropic) converge on the same internal message format. HaxJobs only needs chat_completions. |

## Key source files to reference during implementation

| File | Lines | What to copy |
|------|-------|------|
| `hermes-source/agent/oneshot.py` | 180 | Single-turn template pattern + `_strip_code_fence()` |
| `hermes-source/tools/registry.py` | ~200 | Tool registration + dispatch with error wrapping |
| `hermes-source/agent/prompt_builder.py` | Check `build_context_files_prompt()` + `load_soul_md()` | SOUL.md loading pattern + context file priority |
| `hermes-source/tools/web_tools.py` | ~200 | `web_search` + `web_extract` implementations |
| `pi-source/dist/core/tools/index.js` | Factory switch pattern | Tool dispatch simplicity |

## What NOT to copy (confirmed by docs)

- **Agent loop turn lifecycle** — HaxJobs evaluation is single-turn, scraping is 2-3 turns max
- **Fallback model system** — DeepSeek goes down → user sees an error, doesn't need 8-provider cascade
- **Session persistence with FTS5** — HaxJobs has SQLite via its own DB, not via Hermes' session store
- **Interruptible API calls** — HaxJobs is headless/cron, nobody is pressing Ctrl+C
- **Gateway/ACP/Batch Runner entry points** — HaxJobs has one entry point: `haxjobs start`
- **Dangerous command detection** — HaxJobs tools don't run shell commands
