# HaxJobs Native Agent — Architecture Analysis

Analysis of Pi coding agent and Hermes agent source for building the HaxJobs native agent harness.
Sources at `pi-source/` and `hermes-source/` in this directory.

## 1. Core Agent Loop

### Pi's approach
File: `pi-source/dist/core/agent-session.js` (108KB compiled JS)

Pi's loop is a turn-based conversation: user message → build prompt → LLM call → parse response → execute tools → loop. The compiled code is hard to trace, but the pattern visible in the TypeScript declarations shows:

- `agent-session-runtime.d.ts` defines `AgentSessionRuntime` with methods for `sendMessage`, `handleToolCalls`
- Tools are resolved at creation time via factory pattern: `createToolDefinition(name, cwd, options)` returns the LLM-facing schema; `createTool(name, cwd, options)` returns the executor
- No multi-turn orchestration in the tool layer — tools are stateless single-call functions

### Hermes' approach
File: `hermes-source/agent/conversation_loop.py` (286KB, ~5K lines)

The full conversation loop is `run_conversation()` inside `AIAgent`. Key flow:
1. Build system prompt (includes skills, memory, context files)
2. Build user turn context
3. Call model with retry/fallback logic
4. Parse response — if tool calls, dispatch (sequential or concurrent)
5. Feed tool results back as messages
6. Check context window — compress if needed
7. Post-turn hooks (memory update, skill review nudge)

### What HaxJobs needs

**Copy from Hermes**: the `run_oneshot()` pattern in `oneshot.py` (180 lines). It's exactly what plan 039 implements — stateless single-turn with template registry. HaxJobs evaluation, CV extraction, and wizard questions are all single-turn.

**Skip**: the full multi-turn conversation loop. HaxJobs doesn't need it for v1. When scraping a careers page agentically, we need 2-3 turns with tools — that's `Agent.run()` from plan 043, not a full conversation loop.

**Key lines to copy** (Hermes `oneshot.py`):
```python
# Line 133-155: clean single-turn pattern
messages = []
if instructions.strip():
    messages.append({"role": "system", "content": instructions})
messages.append({"role": "user", "content": user_input})
response = call_llm(
    task=task, messages=messages, max_tokens=max_tokens,
    temperature=temperature, timeout=timeout, main_runtime=main_runtime,
)
text = extract_content_or_reasoning(response).strip()
return _strip_code_fence(text)
```

And the template registry pattern (lines 100-111):
```python
PROMPT_TEMPLATES: Dict[str, PromptTemplate] = {
    "commit_message": _commit_message_template,
}
```

Adapted for HaxJobs: template registry for evaluation prompts, CV extraction prompts, wizard question prompts.

## 2. Tool System

### Pi's approach
File: `pi-source/dist/core/tools/index.js`

Pi has exactly 7 hard-coded tools: `read`, `bash`, `edit`, `write`, `grep`, `find`, `ls`. Each is a file-system operation. Tools are created via factories:
```javascript
export function createToolDefinition(toolName, cwd, options) {
    switch (toolName) {
        case "read": return createReadToolDefinition(cwd, options?.read);
        // ... 6 more
    }
}
```

This is beautifully minimal. No registry, no decorators — just a switch statement. The LLM gets the tool definitions in its system prompt, calls them by name, and the switch dispatches to the right executor.

### Hermes' approach
File: `hermes-source/agent/tool_executor.py` (1.6K lines)

Massive tool dispatch system with:
- Sequential and concurrent execution
- Budget enforcement (character limits per tool result)
- Thread propagation for subprocess tools
- Guardrails (destructive command detection)
- Multimodal tool result handling
- Tool preview/summary for TUI display

Way too much for HaxJobs.

### What HaxJobs needs

**Copy from Pi**: the factory pattern. It's 20 lines, zero dependencies, and self-documenting.

```python
# HaxJobs version — plans 039/043
TOOL_REGISTRY = {
    "web_search": {"schema": WEB_SEARCH_SCHEMA, "fn": web_search},
    "fetch_page": {"schema": FETCH_PAGE_SCHEMA, "fn": fetch_page},
}

def get_tool_definitions(names=None):
    """Return OpenAI-compatible tool schemas for registered tools."""
    names = names or list(TOOL_REGISTRY)
    return [TOOL_REGISTRY[n]["schema"] for n in names if n in TOOL_REGISTRY]

def execute_tool(name, args):
    """Execute a registered tool and return its result."""
    if name not in TOOL_REGISTRY:
        return f"Unknown tool: {name}"
    return TOOL_REGISTRY[name]["fn"](**args)
```

**Skip**: Hermes' concurrency, budget enforcement, thread propagation, guardrails, multimodal handling. HaxJobs tools are simple: search web, fetch page. No subprocess, no file ops.

## 3. Context Management

### Pi's approach
Pi loads context from `AGENTS.md` files in the project directory hierarchy (from `resource-loader.js`). It also has a `compaction/` directory for conversation compression. The skill system injects additional context into the system prompt.

### Hermes' approach
File: `hermes-source/agent/context_compressor.py` (3K lines)

Sophisticated context compression:
- Uses a cheaper auxiliary model to summarize middle turns
- Structured summary with historical task/state/pending sections
- Clear separator between compressed history and active conversation
- Token-budget-based tail protection
- Iterative updates (preserves info across multiple compactions)

The SUMMARY_PREFIX (lines 54-72) is a masterpiece of prompt engineering — it tells the model that compressed content is reference-only:
```
[CONTEXT COMPACTION — REFERENCE ONLY] Earlier turns were compacted 
into the summary below. This is a handoff from a previous context 
window — treat it as background reference, NOT as active instructions.
```

### What HaxJobs needs

**For v1**: nothing. Single-turn evaluation fits easily within context windows (JD + profile = ~40K tokens max, DeepSeek handles 128K).

**For future (plan 043+)**: copy Hermes' SUMMARY_PREFIX pattern when we need multi-turn scraping. When an agent scrapes 3 pages across 10 turns, compress turns 1-8 into a summary and keep turns 9-10 active.

## 4. Skills System

### Pi's approach
File: `pi-source/dist/core/skills.js` (390 lines)

Skills are directories containing `SKILL.md` with frontmatter. Key patterns:
- Validation: name ≤64 chars, lowercase alphanumeric + hyphens only, no leading/trailing/consecutive hyphens
- Frontmatter parsing: YAML frontmatter for metadata (name, description, tools, etc.)
- Ignore file support: `.gitignore`/`.ignore`/`.fdignore` respected within skill dirs
- Skills loaded from `~/.pi/agent/skills/` and workspace-specific paths

The skill's content gets injected into the system prompt. Tools can be gated by active skills.

### Hermes' approach
File: `hermes-source/agent/prompt_builder.py` (2K lines)

Monolithic prompt builder that assembles the system prompt from:
- Identity (default soul)
- Platform hints (OS, shell, date)
- Skills index (list of available skills with conditions)
- Context files (AGENTS.md, SOUL.md)
- Memory (persistent user facts)
- Ephemeral prompts (task-specific instructions)

Skill loading is in `skill_utils.py` with condition matching (platform, environment, file patterns).

### What HaxJobs needs

**Copy from Pi**: the skill directory convention (`SKILL.md` + frontmatter). HaxJobs skills would be:
```
~/.haxjobs/skills/
  evaluate-job/
    SKILL.md          # System prompt for job evaluation
  discover-jobs/
    SKILL.md          # System prompt for job discovery
  build-scraper/
    SKILL.md          # System prompt for scraper building
```

Each skill is a markdown file with YAML frontmatter:
```yaml
---
name: evaluate-job
description: Evaluate a job listing against the user's profile
tools: [web_search]
---
You are a job-candidate fit evaluator...
[system prompt content]
```

**Skip**: Hermes' monolithic `_build_system_prompt()` — it's 2K lines of platform detection, skill conditions, context file scanning. HaxJobs is a single-purpose agent, not a general-purpose one.

## 5. Provider/Model Abstraction

### Pi's approach
Pi uses a provider abstraction layer. Models are configured in `~/.pi/config.yaml` with provider aliases. The compiled code in `dist/providers/` (none found in npm package — likely in the private TypeScript source).

### Hermes' approach
File: `hermes-source/agent/auxiliary_client.py` (300KB — massive)

The `call_llm()` function is the single entry point for all LLM calls. It handles:
- Provider resolution: main provider → OpenRouter → Nous Portal → custom endpoint → native Anthropic → direct API-key providers
- Automatic fallback on 402 (payment exhaustion) and 429 (rate limit)
- Model routing based on task type (title_generation, context_compression, etc.)
- Multimodal content handling

Too heavy for HaxJobs but the concept is right.

### What HaxJobs needs

HaxJobs' abstraction is already right — it's in the provider config (`~/.haxjobs/config.toml`). The `openai` Python package already handles any OpenAI-compatible API (DeepSeek, OpenAI, Groq, Together, local llama.cpp). The `Agent` class just needs `base_url` + `api_key` + `model` — that's 3 config values, not 300KB of fallback logic.

**Future**: if HaxJobs ever needs provider fallback (DeepSeek down → fall back to OpenAI), add a `fallback_providers` list to `config.toml`. Don't build Hermes' 8-provider cascade.

## 6. Pi's Minimalist Philosophy — What "Get Out of the LLM's Way" Means

From analyzing the code vs Hermes:

| Aspect | Pi | Hermes |
|--------|-----|--------|
| Built-in tools | 7 (read, bash, edit, write, grep, find, ls) | 30+ (browser, image gen, voice, etc.) |
| Tool registration | Switch statement | Full registry with guardrails, budgets |
| System prompt | Skills + AGENTS.md context | Identity + platform + skills + memory + context files + ephemeral |
| Context management | Simple compaction | 3K-line compressor with structured summaries |
| Provider layer | Thin abstraction | 300KB auxiliary_client with 8-provider cascade |
| Codebase | ~6K TS files but core loop is tight | 2756 Python files, many 100KB+ |

Concrete design principles visible in Pi's code:

1. **Only 7 tools** — the LLM has everything it needs to work with a codebase and nothing it doesn't. Every additional tool is a decision the LLM can make wrong.

2. **Skills extend, code doesn't** — behavior changes happen in `SKILL.md` files, not in new `if` branches. The system prompt is the extension point.

3. **Tool definitions are the interface** — the LLM sees tool schemas, not API wrappers. The schema IS the contract.

4. **No assumptions about what the LLM should do** — Pi doesn't have "workflows" or "patterns." The LLM reads files, runs commands, and decides. That's it.

## 7. What HaxJobs Should Copy — The Implementation Plan

### From Hermes (Python patterns, can copy directly):

**CRITICAL — `run_oneshot()` pattern** (`agent/oneshot.py:133-155`)
- Template registry for prompts
- Clean single-turn: system message → user message → call → strip fence
- HaxJobs: use for evaluation, CV extraction, wizard questions

**CRITICAL — `_strip_code_fence()`** (`agent/oneshot.py:163-170`)
- Models sometimes wrap JSON in ``` fences
- Strip exactly one layer — don't recursively strip

**USEFUL — `SUMMARY_PREFIX`** (`agent/context_compressor.py:54-72`)
- The "compacted content is reference-only" instruction
- HaxJobs: use when doing multi-turn agent scraping (plan 043+)

### From Pi (patterns, implement in Python):

**CRITICAL — Tool factory pattern** (`dist/core/tools/index.js`)
- Switch-based dispatch, one function per tool
- Tool definition (LLM schema) and tool executor (Python function) created together

**CRITICAL — Skill directory convention** (`dist/core/skills.js`)
- `SKILL.md` with YAML frontmatter
- Skills inject into system prompt
- Tools gated by active skill

**USEFUL — Context file loading** (`dist/core/resource-loader.js`)
- Load `AGENTS.md` from directory hierarchy
- HaxJobs: load `haxjobs.toml` config + profile JSON + AGENTS.md

### What to skip entirely:
- Hermes' `conversation_loop.py` (5K lines) — HaxJobs doesn't need multi-turn conversation
- Hermes' `tool_executor.py` (1.6K lines) — HaxJobs has 3 tools, not 30
- Hermes' `context_compressor.py` (3K lines) — v1 doesn't need compression
- Hermes' `auxiliary_client.py` (300KB) — the `openai` package is the client
- Pi's `agent-session.js` (108KB) — HaxJobs doesn't need an interactive REPL

## 8. Recommended Implementation Order

### Plan 039 (bare-minimum agent, ~40 lines):
```python
# haxjobs/agent/agent.py
class Agent:
    def run(self, prompt, system=None): ...
    def run_structured(self, prompt, system=None, json_schema=None): ...
```
This is `run_oneshot()` from Hermes, adapted for the `openai` package.

### Plan 043 (full agent, ~150 lines):
Adds:
- `registry.py` — `ToolRegistry` with `@tool` decorator (Hermes pattern simplified)
- `tools.py` — `web_search`, `fetch_page` (DuckDuckGo + requests)
- Multi-turn `run_with_tools()` method on Agent

### Plan 057 (future — skills + context engineering):
- `haxjobs/skills/` directory with `evaluate-job/SKILL.md`, `discover-jobs/SKILL.md`
- Skill loader: parse frontmatter, inject into system prompt
- Context engineering: how HaxJobs crafts the right prompt for each task type

## 9. HaxJobs Agent Design — Final Shape

```
haxjobs/agent/
  __init__.py       # re-exports Agent
  agent.py          # ~80 lines: Agent class (run, run_structured, run_with_tools)
  registry.py       # ~30 lines: ToolRegistry (register, get, get_schemas)
  tools.py          # ~40 lines: web_search, fetch_page
  config.py         # ~20 lines: load_provider_config()

haxjobs/skills/     # future plan 057
  evaluate-job/
    SKILL.md        # System prompt for job evaluation
  discover-jobs/
    SKILL.md        # System prompt for job discovery
  build-scraper/
    SKILL.md        # System prompt for building site scrapers
```

Total: ~170 lines of Python for the core agent. Skills add markdown files — no code.

That's the Pi philosophy applied to Python: minimal core, skills extend behavior, LLM decides what tools to call.
